"""
Persistent state for the copy trader.
Tracks: paper balance, open positions, per-wallet PnL, trade journal entries.
"""
import json
from pathlib import Path
from datetime import datetime
import time

CACHE = Path("/opt/data/hermes_work/bot/copy_trader/state")
CACHE.mkdir(parents=True, exist_ok=True)

# Files
ACCOUNT_FILE = CACHE / "account.json"
POSITIONS_FILE = CACHE / "positions.json"
JOURNAL_FILE = CACHE / "journal.jsonl"
PERFORMANCE_FILE = CACHE / "performance.json"

# Default paper account settings
PAPER_STARTING_BALANCE = 2.0  # 2 SOL like the real user account
SIMULATED_FEE_PCT = 0.0030  # 0.30% total fee (Jupiter ~0.2% + priority fee + slippage buffer)
SIMULATED_SLIPPAGE_PCT = 0.0050  # 0.50% slippage buffer


def load_account():
    """Load paper balance or initialize."""
    if ACCOUNT_FILE.exists():
        return json.load(open(ACCOUNT_FILE))
    init = {
        "starting_balance_sol": PAPER_STARTING_BALANCE,
        "current_balance_sol": PAPER_STARTING_BALANCE,
        "total_fees_paid_sol": 0.0,
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "realized_pnl_sol": 0.0,
        "created_at": int(time.time()),
        "mode": "PAPER",  # PAPER = no real SOL
    }
    save_account(init)
    return init


def save_account(state):
    """Persist account state."""
    state["updated_at"] = int(time.time())
    ACCOUNT_FILE.write_text(json.dumps(state, indent=2))


def load_positions():
    """Open positions we currently hold (paper tokens we bought but haven't sold)."""
    if POSITIONS_FILE.exists():
        return json.load(open(POSITIONS_FILE))
    return {}


def save_positions(positions):
    POSITIONS_FILE.write_text(json.dumps(positions, indent=2))


def load_journal():
    """All trade events (one line each)."""
    if JOURNAL_FILE.exists():
        with open(JOURNAL_FILE) as f:
            return [json.loads(line) for line in f if line.strip()]
    return []


def append_journal(entry):
    """Append one trade event to the journal log."""
    entry["logged_at"] = int(time.time())
    with open(JOURNAL_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def load_performance():
    """Per-wallet performance aggregator."""
    if PERFORMANCE_FILE.exists():
        return json.load(open(PERFORMANCE_FILE))
    return {}  # wallet_addr -> {trades, wins, losses, realized_pnl, criteria}


def save_performance(perf):
    """Persist per-wallet stats."""
    PERFORMANCE_FILE.write_text(json.dumps(perf, indent=2))


def update_performance(wallet, trade_outcome, criteria):
    """Update per-wallet performance after a paper trade completes."""
    perf = load_performance()
    if wallet not in perf:
        perf[wallet] = {
            "trades": 0, "wins": 0, "losses": 0,
            "realized_pnl_sol": 0.0, "first_seen": int(time.time()),
            "criteria": criteria,
            "trade_log": []  # list of {time, pnl}
        }
    p = perf[wallet]
    p["trades"] += 1
    if trade_outcome["pnl"] >= 0:
        p["wins"] += 1
    else:
        p["losses"] += 1
    p["realized_pnl_sol"] += trade_outcome["pnl"]
    p["trade_log"].append({
        "time": int(time.time()),
        "pnl": trade_outcome["pnl"],
        "token": trade_outcome.get("token_mint", "?"),
        "trade_type": trade_outcome.get("trade_type", "?"),
    })
    save_performance(perf)
