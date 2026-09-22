"""
Entry point for the copy trader.
Runs continuously, polls watched wallets, simulates paper trades.
"""
import sys
import time
import json
from pathlib import Path

# Add bot dir to path so we can use bot.copy_trader.*
import sys
sys.path.insert(0, "/opt/data/hermes_work")

# We're running from bot/ directory, so import copy_trader directly
from copy_trader.trader import CopyTrader
from copy_trader.state import (
    load_account, save_account, load_positions, load_journal, load_performance
)

CACHE = Path("/opt/data/hermes_work/bot/copy_trader/state")


def main():
    print("=" * 60)
    print("COPY TRADER — REAL-TIME PAPER TRADING")
    print("=" * 60)

    # Initialize account if needed
    account = load_account()
    print(f"\nAccount initialized: {account['starting_balance_sol']} SOL paper balance")
    print(f"Current balance: {account['current_balance_sol']:.4f} SOL")
    print(f"Total trades: {account['total_trades']}")
    print(f"Realized PnL: {account['realized_pnl_sol']:+.4f} SOL")

    trader = CopyTrader()
    print(f"\nWatching {len(trader.watchers)} wallets:")
    for w in trader.watchers:
        crit = trader.targets[0] if trader.targets else {}
        # Show wallet address
        info = trader.targets[0] if trader.targets else {}
        if isinstance(info, dict):
            pass
        # Lookup criteria
        for t in trader.targets:
            if t["wallet"] == w:
                print(f"  - {w[:14]}... | PnL +{t.get('pnl', 0):.2f} SOL | held {t.get('hold_hours', 0):.0f}h | buys={t.get('buy_txs', 0)}")
                break

    print(f"\nPolling every 2s...")
    print("=" * 60)

    tick_count = 0
    while True:
        try:
            events = trader.tick()
            if events:
                for action, wallet, swap, sim in events:
                    if action == "buy":
                        print(f"[BUY ] {wallet[:14]}...  token {swap['token_mint'][:8]}...  "
                              f"our {sim['actual_sol_after_fees']:.4f} SOL (target {swap['sol_amount']:.4f})  "
                              f"fee {sim['fee_sol']:.5f}  slip {sim['slippage_sol']:.5f}")
                    else:
                        pnl = sim['sol_received_net']  # already net of fees
                        print(f"[SELL] {wallet[:14]}...  +{pnl:.4f} SOL received")

                # Print balance
                cur = load_account()
                print(f"  → balance: {cur['current_balance_sol']:.4f} SOL | realized: {cur['realized_pnl_sol']:+.4f} SOL")
            tick_count += 1
            if tick_count % 30 == 0:
                cur = load_account()
                print(f"[t={tick_count*2}s] balance {cur['current_balance_sol']:.4f} SOL | "
                      f"trades {cur['total_trades']} | "
                      f"winning {cur['winning_trades']} losing {cur['losing_trades']}")
        except KeyboardInterrupt:
            print("\nShutting down gracefully.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
