#!/usr/bin/env python3
"""Webhook v8 - lower dust filter + handle USDC-funded swaps."""
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, "/opt/data/hermes_work")

from flask import Flask, request, jsonify
from bot.copy_trader.trader import simulate_paper_trade, execute_paper_buy, execute_paper_sell

app = Flask(__name__)
WATCHED = set()
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
QUOTE_TOKENS = {WSOL, USDC}


def update_dashboard_state():
    """Write current state to dashboard cache file."""
    try:
        account = load_account()
        journal = Path("/opt/data/hermes_work/bot/copy_trader/state/journal.jsonl")
        trades = [json.loads(line) for line in journal.read_text().splitlines() if line.strip()]
        recent = trades[-15:][::-1]
        
        state = {
            "updated_at": int(time.time()),
            "starting_balance_sol": account["starting_balance_sol"],
            "current_balance_sol": account["current_balance_sol"],
            "total_trades": account["total_trades"],
            "realized_pnl_sol": account.get("realized_pnl_sol", 0),
            "total_fees_sol": account["total_fees_paid_sol"],
            "winning_trades": account.get("winning_trades", 0),
            "losing_trades": account.get("losing_trades", 0),
            "recent_trades": recent,
        }
        Path("/opt/data/hermes_work/bot/copy_trading/cache/copy_trader_state.json").write_text(json.dumps(state, indent=2))
    except Exception as e:
        print(f"[STATE UPDATE ERR] {e}", flush=True)


# Lower threshold: target_sol >= 0.005 ($1)
MIN_TARGET_SOL = 0.005
SOL_PRICE_USD = 200  # Approx

def init():
    global WATCHED
    targets_path = Path("/opt/data/hermes_work/bot/copy_trading/cache/copy_targets.json")
    data = json.loads(targets_path.read_text())
    WATCHED = set(t["wallet"] for t in data.get("targets", []))
    print(f"[INIT] {len(WATCHED)} wallets, MIN_TARGET_SOL={MIN_TARGET_SOL}", flush=True)


def decode_swap(ev, watched_wallet):
    """Decode swap with USDC support + relaxed dust filter."""
    sol_change = 0
    for ad in ev.get("accountData", []):
        if ad.get("account") == watched_wallet:
            sol_change = ad.get("nativeBalanceChange", 0) / 1e9
            break
    
    transfers_in = []
    transfers_out = []
    for tt in ev.get("tokenTransfers", []):
        if tt.get("toUserAccount") == watched_wallet:
            transfers_in.append(tt)
        elif tt.get("fromUserAccount") == watched_wallet:
            transfers_out.append(tt)
    
    received_base = next((t for t in transfers_in if t.get("mint") not in QUOTE_TOKENS), None)
    sent_base = next((t for t in transfers_out if t.get("mint") not in QUOTE_TOKENS), None)
    
    if received_base and not sent_base:
        side = "buy"
        token = received_base
    elif sent_base and not received_base:
        side = "sell"
        token = sent_base
    elif sent_base and received_base:
        if sol_change > 0:
            side = "sell"; token = sent_base
        else:
            side = "buy"; token = received_base
    else:
        return None
    
    # Estimate trade value in SOL terms
    # 1. SOL moved
    target_sol = abs(sol_change)
    
    # 2. WSOL moved (could be wrapped SOL)
    for tt in transfers_in + transfers_out:
        if tt.get("mint") == WSOL:
            if tt.get("fromUserAccount") == watched_wallet:
                target_sol = max(target_sol, float(tt.get("tokenAmount", 0)))
    
    # 3. USDC moved → convert to SOL
    for tt in transfers_in + transfers_out:
        if tt.get("mint") == USDC and tt.get("fromUserAccount") == watched_wallet:
            usdc_amt = float(tt.get("tokenAmount", 0))
            target_sol = max(target_sol, usdc_amt / SOL_PRICE_USD)
    
    # Filter
    if target_sol < MIN_TARGET_SOL:
        return None
    
    token_amount = float(token.get("tokenAmount", 0))
    
    return {
        "side": side,
        "sol_amount": target_sol,
        "token_amount": token_amount,
        "token_mint": token.get("mint", ""),
        "sig": ev.get("signature", ""),
        "slot": ev.get("slot", 0),
    }


@app.route("/webhook/solana", methods=["POST"])
def webhook():
    try:
        events = request.get_json(force=True, silent=True) or []
        if not isinstance(events, list):
            events = [events]
        
        swaps_count = 0
        for ev in events:
            watched_match = None
            for ad in ev.get("accountData", []):
                if ad.get("account") in WATCHED:
                    watched_match = ad.get("account")
                    break
            
            if not watched_match:
                continue
            
            swap = decode_swap(ev, watched_match)
            if not swap:
                continue
            
            swaps_count += 1
            print(f"[HIT] {watched_match[:14]}... {swap['side']} {swap['token_mint'][:10]}... target={swap['sol_amount']:.4f}SOL (${swap['sol_amount']*200:.0f})", flush=True)
            
            sim = simulate_paper_trade(swap)
            if sim is None:
                continue
            
            if swap["side"] == "buy":
                execute_paper_buy(watched_match, swap, sim)
                print(f"[BUY] our_sol={sim['actual_sol_after_fees']:.4f}", flush=True)
            else:
                result = execute_paper_sell(watched_match, swap, sim)
                if result is None:
                    print(f"[SKIP-SELL] no position", flush=True)
                else:
                    pnl = sim.get("sol_received_net", 0) - sim.get("cost_basis_sol", 0)
                    print(f"[SELL] pnl={pnl*1000:+.2f}mSOL", flush=True)
        
        return jsonify({"status": "ok", "swaps": swaps_count}), 200
    except Exception as e:
        import traceback
        print(f"[CRASH] {e}", flush=True)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "watched": len(WATCHED)}), 200


if __name__ == "__main__":
    init()
    app.run(host="0.0.0.0", port=8765, debug=False, use_reloader=False)
