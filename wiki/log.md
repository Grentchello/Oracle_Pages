
## [2026-09-17 18:56 UTC] eval | 2h cron auto-eval (window: Sep 17 16:52 → 18:56 UTC)
- **Window since last eval (~2h)**: **0 new trades** (3,572 → 3,572). Bot is alive — Solana runner PID 507 still ticking every 60s and bot.py edits ARE active (runner.py spawns fresh subprocess per tick, so each tick re-imports the latest bot.py). State.json mtime fresh (18:55 UTC). Zero trades means candidates are failing at v9.1 liquidity gate + v9.4 (8 SOL bonding curve floor) + v8.9 (3 min age filter, just tightened at 16:52 UTC) — combined filtering is now very tight.
- **Honest performance read** (per Grant's pattern — "reported balance inflated by slippage, phantom TP, or balance math bugs"):
  - **Lifetime paper PnL: +25.525 SOL** (3,572 trades, 45.3% WR, 1,617W/1,955L) — pre-v9.3 era dominates this number via v9.0 mid-price sim (no slippage modeled). Treat as upper bound.
  - **Current balance: 1.1806 SOL** vs Sep 16 14:11 reset of 2.0 SOL = **-0.8194 SOL realized (-41.0%) since reset**. This is the honest slippage-aware read.
  - **Last 50 trades**: -0.7894 SOL, **43/50 = 86% ghost rate** (v9.3 caught pool=0 exits and recorded 0 SOL received). Pre-v8.9 age-tighten was the bleeding window.
- **All-time by category**: tp_win 1,071 trades (+46.95 SOL), partial_tp 556 (+6.75), other_loss 1,677 (-19.71), rapid_loss 164 (-5.05), ghost_rug 93 (-2.87), override 11 (-0.56). TP-full is the proven gainer; ghost-rug is honest but cumulative.
- **Active filter stack as of this eval**:
  - v8.7 mechanical (DO NOT CHANGE): POSITION_SIZE_SOL=0.02, RESERVE_SOL=0.02, HARD_STOP_LOSS=-25%, MAX_HOLD=30min, TP+50% auto-full.
  - v8.9 age filter: <3 min rejected (tightened from 0.5 min at 16:52 UTC prior eval).
  - v9.1 liquidity gate.
  - v9.4 bonding curve floor: 8 SOL (reverted from v9.5 at 12:43 UTC).
  - v9.3 hard liquidity gate on exit (the source of the honest ghost-exit logs).
- **Root cause assessment**: the structural problem is pump.fun bonding-curve sniper drain (curves that pass 8 SOL depth check at entry are <2 SOL by exit). v9.3 ghost-exit honesty means we now correctly record 0 SOL on these drains instead of paper gains. The age-filter tightening (0.5→3 min) is a parameter tweak aimed at the sniper-drain window — should reduce ghost rate on entries that DO fire, but no entries have fired yet to verify.
- **Decision: NO PARAMETER CHANGES THIS RUN**. Reasoning:
  1. 0 trades in this 2h window → nothing to evaluate parameter performance on. The age-tighten hypothesis needs ≥10 post-deploy trades to validate.
  2. Mechanical v8.7 rules (HARD_STOP_LOSS, MAX_HOLD, TP+50%, POSITION_SIZE, RESERVE, MAX_POSITIONS) are explicit "do not change" per session instructions.
  3. v9.4 (8 SOL floor, reverted at 12:43 UTC) is also untested post-revert — sample size = 0 trades. Cannot judge.
  4. The 86% ghost rate in the last 50 trades is a window of older data (mostly pre-12:43 v9.5 era); the v8.9 age-tighten + v9.4 revert have 0 post-deploy samples. Premature to escalate.
- **Next eval triggers** (carrying forward):
  - If at next 2h window n_post_age_tighten (now 0) reaches ≥10 trades AND ghost rate > 50%, escalate v8.9 age filter from 3 min → 5 min (further sniper-drain protection).
  - If n_post_age_tighten ≥ 10 AND ghost rate < 50%, we've found the working combination — hold steady.
  - If still 0 trades at next eval, the combined filter stack (v8.9 3min + v9.1 + v9.4 8SOL) is too tight. Easing v9.4 back toward 6 SOL is a single-param option; loosening v8.9 age from 3 → 2 min is another. Do not relax both at once.
- **Bot status**: running, no halt. Runner.py spawns fresh bot.py each tick so edits to bot.py take effect immediately on the next tick. Solana runner PID 507 alive since Sep 15. Base runner PID 294355 alive. Trade count: 3,572. Balance: 1.1806 SOL. Open positions: 0.


## [2026-09-17 20:57 UTC] eval | 2h cron auto-eval (window: Sep 17 18:56 → 20:57 UTC)
- **Window since last eval (~2h)**: **0 new trades** (3,572 → 3,572). Bot alive, runner PID 507 ticking every 60s. State.json mtime fresh.
- **Window since v8.9 age-tighten at 16:52 UTC (~4h)**: **0 trades**. Filter stack (v8.9 3min + v9.1 $1k DEX + v9.4 8 SOL bonding) is now over-blocking — combined gates are tight enough that no candidate passes.
- **Window's 22 trades (3,550→3,572) all happened 01:39–02:57 UTC, BEFORE the 16:52 tighten** — they reflect pre-fix performance, not current state. Net -0.3839 SOL realized in window, 90.9% ghost rate (20/22), 1 real win (+0.0011), 1 real loss (-0.0050).
- **Balance**: 1.1806 SOL, down -0.3639 SOL since last eval (1.5444). Down -0.8194 SOL (-41.0%) since Sep 16 14:11 reset.
- **Lifetime**: 3,572 trades, 45.3% WR, +25.525 SOL paper PnL (pre-v9.3 era dominates via v9.0 mid-price sim — treat as upper bound).
- **DECISION — single-param fix per prior eval's pre-committed trigger**: eased v8.9 age filter **3.0 → 2.0 min** (line 639 of bot.py). This is the conservative option vs easing v9.4 SOL floor (8→6 SOL). v8.7+ mechanical rules preserved unchanged (POSITION_SIZE_SOL=0.02, RESERVE_SOL=0.02, HARD_STOP_LOSS=-25%, MAX_HOLD=30min, TP+50% auto-full).
- **Rationale for choosing age-ease over SOL-floor-ease**: pump.fun sniper-drain data shows the 30-90s window is the bleeding window. A 2-min floor still excludes that window while allowing tokens with 2-3 min of organic volume through. The 8 SOL bonding-curve floor has separate validation needs (snipers can drain 8 SOL too).
- **Next eval trigger**: if v8.9 2-min window produces ≥10 trades AND ghost rate > 50%, escalate to v8.9 5 min. If ≥10 trades AND ghost rate < 50%, we've found the working combination — hold. If still 0 trades at next eval, the combined stack is still over-blocking — escalate to easing v9.4 (8 → 6 SOL) as the next single-param change.
- **Bot status**: running, no halt. Solana runner PID 507 alive. bot.py v8.9 age filter updated from 3.0 → 2.0 min. Edits take effect on next tick (runner.py spawns fresh subprocess per tick).
