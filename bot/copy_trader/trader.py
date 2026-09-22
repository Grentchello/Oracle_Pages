"""
Real-time copy trader.
Polls watched wallets via Solana RPC every second, parses their swaps,
and simulates paper copy trades with realistic fees + slippage.
"""
import json
import time
import urllib.request
from pathlib import Path
from datetime import datetime

from .state import (
    load_account, save_account, load_positions, save_positions,
    append_journal, load_performance, update_performance,
    SIMULATED_FEE_PCT, SIMULATED_SLIPPAGE_PCT, PAPER_STARTING_BALANCE,
)
from .decoder import decode_swap

RPC = "https://api.mainnet-beta.solana.com"
TARGETS_FILE = Path("/opt/data/hermes_work/bot/copy_trading/cache/copy_targets.json")
# Path to the wallet targets — load them on init

# Poll interval (seconds)
POLL_INTERVAL = 2.0


def rpc_call(method, params, retries=3):
    """Make Solana RPC call with retry."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(RPC, data=body,
                                          headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except Exception as e:
            last_err = str(e)
            if "RATE" in last_err or "429" in last_err:
                time.sleep(60)
            else:
                time.sleep(2)
    return None


def get_recent_signatures(wallet, since_sig=None):
    """Get recent sigs for wallet. Optionally filter by since_sig (only newer)."""
    r = rpc_call("getSignaturesForAddress",
                 [wallet, {"limit": 20}])
    if not r or "result" not in r:
        return []
    sigs = r["result"]
    out = []
    for s in sigs:
        if since_sig is None or s["signature"] == since_sig:
            out.append(s)
            if since_sig:
                break
    return out


def get_transaction(sig):
    """Get full transaction details."""
    return rpc_call("getTransaction",
                    [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}])


def fetch_targets():
    """Load the list of wallets to copy-trade."""
    if not TARGETS_FILE.exists():
        return []
    data = json.load(open(TARGETS_FILE))
    return data.get("targets", [])


def wallet_criteria(target):
    """Return user-friendly criteria for a wallet (for dashboard display)."""
    return {
        "criteria": [
            "fresh_wallet tag from GMGN",
            f"≥48h funding hold time ({target.get('hold_hours', 0):.0f}h actual)",
            f"profitable ({target.get('pnl', 0):.2f} SOL)",
            f"avg buy size ≤2 SOL ({target.get('avg_buy', 0):.2f} actual)",
            "wallet age ≤7 days",
        ],
        "gmgn_pnl_sol": target.get("pnl", 0),
        "funding_source": target.get("funding", "?"),
        "hold_hours": target.get("hold_hours", 0),
        "buy_txs": target.get("buy_txs", 0),
    }


def simulate_paper_trade(swap_signal):
    """Simulate copying this swap at our paper size with fees."""
    # Strategy: use 10% of paper balance per trade, capped at 0.1 SOL
    account = load_account()
    balance = account["current_balance_sol"]

    # Position size = 10% of balance, capped
    position_size_pct = 0.10
    ideal_size = balance * position_size_pct
    actual_size = min(ideal_size, 0.1)  # Max 0.1 SOL

    if actual_size < 0.001:
        # Too small to trade
        return None

    # Calculate simulated fee (0.30%)
    fee_sol = actual_size * SIMULATED_FEE_PCT
    # Slippage (worst case)
    slippage_sol = actual_size * SIMULATED_SLIPPAGE_PCT
    net_sol = actual_size - fee_sol - slippage_sol

    # For BUY: spend net_sol, get tokens
    # For SELL: we're selling tokens we own
    if swap_signal["side"] == "buy":
        actual_size_sol = actual_size
        tokens_acquired = (net_sol / swap_signal["sol_amount"]) * swap_signal["token_amount"]
        return {
            "action": "BUY",
            "target_sol_spent": actual_size,
            "actual_sol_after_fees": net_sol,
            "tokens_acquired": tokens_acquired,
            "fee_sol": fee_sol,
            "slippage_sol": slippage_sol,
            "ratio_target_to_us": actual_size / swap_signal["sol_amount"],
        }
    else:  # SELL
        # We need to sell the tokens we hold for this mint
        positions = load_positions()
        mint_key = swap_signal["token_mint"]
        if mint_key not in positions or positions[mint_key]["tokens"] <= 0:
            return None  # We have nothing to sell
        tokens_held = positions[mint_key]["tokens"]
        # Sell proportionally to how the target sold
        target_token_sold = swap_signal["token_amount"]
        target_sol_received = swap_signal["sol_amount"]

        # Sell our tokens proportionally (their sell ratio matches ours)
        sol_received_gross = (tokens_held / target_token_sold) * target_sol_received
        fee_sol = sol_received_gross * SIMULATED_FEE_PCT
        slippage_sol = sol_received_gross * SIMULATED_SLIPPAGE_PCT
        net_sol_received = sol_received_gross - fee_sol - slippage_sol

        return {
            "action": "SELL",
            "tokens_sold": tokens_held,
            "sol_received_gross": sol_received_gross,
            "sol_received_net": net_sol_received,
            "fee_sol": fee_sol,
            "slippage_sol": slippage_sol,
            "ratio_target_to_us": tokens_held / target_token_sold,
        }


def execute_paper_buy(watched_wallet, swap, sim):
    """Record a paper BUY trade."""
    account = load_account()
    positions = load_positions()

    # Debit paper balance
    account["current_balance_sol"] -= sim["actual_sol_after_fees"]
    account["total_fees_paid_sol"] += sim["fee_sol"] + sim["slippage_sol"]
    account["total_trades"] += 1
    save_account(account)

    # Record position
    mint_key = swap["token_mint"]
    if mint_key not in positions:
        positions[mint_key] = {
            "tokens": 0, "sol_spent": 0, "watched_wallet": watched_wallet,
            "entry_sig": swap["sig"], "entry_time": int(time.time()),
        }
    positions[mint_key]["tokens"] += sim["tokens_acquired"]
    positions[mint_key]["sol_spent"] += sim["actual_sol_after_fees"]
    save_positions(positions)

    # Log to journal
    entry = {
        "type": "BUY",
        "watched_wallet": watched_wallet,
        "target_sol": swap["sol_amount"],
        "our_sol": sim["actual_sol_after_fees"],
        "fee_sol": sim["fee_sol"],
        "slippage_sol": sim["slippage_sol"],
        "tokens": sim["tokens_acquired"],
        "token_mint": swap["token_mint"],
        "ratio": sim["ratio_target_to_us"],
        "sig": swap["sig"],
        "slot": swap["slot"],
    }
    append_journal(entry)
    update_performance(
        watched_wallet,
        {"pnl": 0, "token_mint": swap["token_mint"], "trade_type": "buy_pending"},
        wallet_criteria({"hold_hours": 0, "pnl": 0, "avg_buy": 0, "funding": "?", "buy_txs": 0}),
    )
    return entry


def execute_paper_sell(watched_wallet, swap, sim):
    """Record a paper SELL trade."""
    account = load_account()
    positions = load_positions()

    mint_key = swap["token_mint"]
    if mint_key not in positions or positions[mint_key]["tokens"] <= 0:
        return None

    tokens_sold = sim["tokens_sold"]
    cost_basis = positions[mint_key]["sol_spent"] * (tokens_sold / positions[mint_key]["tokens"])
    pnl = sim["sol_received_net"] - cost_basis

    # Credit paper balance
    account["current_balance_sol"] += sim["sol_received_net"]
    account["total_fees_paid_sol"] += sim["fee_sol"] + sim["slippage_sol"]
    account["total_trades"] += 1
    account["realized_pnl_sol"] += pnl
    if pnl >= 0:
        account["winning_trades"] += 1
    else:
        account["losing_trades"] += 1
    save_account(account)

    # Update position (close or reduce)
    positions[mint_key]["tokens"] -= tokens_sold
    positions[mint_key]["sol_spent"] -= cost_basis
    if positions[mint_key]["tokens"] <= 0.0001:
        del positions[mint_key]
    save_positions(positions)

    # Journal
    entry = {
        "type": "SELL",
        "watched_wallet": watched_wallet,
        "tokens_sold": tokens_sold,
        "sol_received_net": sim["sol_received_net"],
        "pnl_sol": pnl,
        "fee_sol": sim["fee_sol"],
        "slippage_sol": sim["slippage_sol"],
        "cost_basis_sol": cost_basis,
        "token_mint": swap["token_mint"],
        "sig": swap["sig"],
        "slot": swap["slot"],
    }
    append_journal(entry)
    update_performance(
        watched_wallet,
        {"pnl": pnl, "token_mint": swap["token_mint"], "trade_type": "sell"},
        wallet_criteria({"hold_hours": 0, "pnl": 0, "avg_buy": 0, "funding": "?", "buy_txs": 0}),
    )
    return entry


class WalletWatcher:
    """Watches one wallet for new swaps."""

    def __init__(self, wallet_info):
        self.wallet = wallet_info["wallet"]
        self.info = wallet_info
        self.last_sig = None
        self.activity_count = 0

    def poll(self):
        """Return new swaps since last poll, or []."""
        r = rpc_call("getSignaturesForAddress", [self.wallet, {"limit": 5}])
        if not r or "result" not in r:
            time.sleep(POLL_INTERVAL)
            return []
        sigs = r["result"]
        if not sigs:
            time.sleep(POLL_INTERVAL)
            return []

        new_sigs = []
        seen_sig = False
        for s in sigs:
            if s["signature"] == self.last_sig:
                seen_sig = True
                break
            if s.get("err"):
                continue
            new_sigs.append(s["signature"])

        if not seen_sig and self.last_sig:
            # Could be we missed the sig (rare); reset if more than 10 sigs
            new_sigs = [s["signature"] for s in sigs[:5] if not s.get("err")]

        swaps = []
        for sig in reversed(new_sigs):  # oldest-first processing
            tx = get_transaction(sig)
            if not tx:
                continue
            swap = decode_swap(tx, self.wallet)
            if swap:
                swaps.append(swap)

        self.last_sig = sigs[0]["signature"] if sigs else self.last_sig
        self.activity_count += 1
        time.sleep(POLL_INTERVAL)
        return swaps


class CopyTrader:
    """Orchestrates multiple WalletWatchers."""

    def __init__(self):
        self.targets = fetch_targets()
        self.watchers = {t["wallet"]: WalletWatcher(t) for t in self.targets}

    def tick(self):
        """One iteration: poll all wallets, process their swaps."""
        events = []
        for wallet, w in self.watchers.items():
            try:
                swaps = w.poll()
                for swap in swaps:
                    sim = simulate_paper_trade(swap)
                    if sim is None:
                        continue
                    if swap["side"] == "buy":
                        entry = execute_paper_buy(wallet, swap, sim)
                        if entry:
                            events.append(("buy", wallet, swap, sim))
                    else:
                        entry = execute_paper_sell(wallet, swap, sim)
                        if entry:
                            events.append(("sell", wallet, swap, sim))
            except Exception as e:
                pass
        return events

    def run_forever(self):
        """Main loop."""
        print(f"Copy trader started, watching {len(self.watchers)} wallets")
        while True:
            try:
                self.tick()
            except KeyboardInterrupt:
                print("\nShutting down.")
                break
            except Exception as e:
                print(f"Tick error: {e}")
                time.sleep(5)
