# 📊 Copy-Trading

**Goal:** Find wallets with proven track record. Monitor their activity to decide what to follow.

## 🧠 Smart Money Wallet List

**903 wallets** found from 62 quality tokens. Top 100 ranked by total realized PnL across winning tokens.

[📊 **Open Live Dashboard** →](./dashboard.html)

**Top 10:**

| # | Wallet | Total PnL (SOL) | Tokens |
|---|--------|-----------------|--------|
| 1 | `Ak4Y5q2S...etYx` `→` [full](https://solscan.io/account/Ak4Y5q2SE8nZkD2oAdnQU1b1pufBGHrpDKgevEyhetYx) | +83,249 | 1 |
| 2 | `7FxjZLcd...nVLS` `→` [full](https://solscan.io/account/7FxjZLcdNEcQMz83xR29h1Ws9mqmeeERrdbH7AFHnVLS) | +51,868 | 1 |
| 3 | `8aLkjkg1...iE9p` `→` [full](https://solscan.io/account/8aLkjkg1BqSSTGMMTKBYri32RFwhSBTKimsxWNP3iE9p) | +44,800 | 1 |
| 4 | `9AZrNV2p...psyP` `→` [full](https://solscan.io/account/9AZrNV2p6qLojEtfrZBFFHpjGGLbjJ39xyYFehVspsyP) | +42,819 | 1 |
| 5 | `AyjCrA7r...3Fjp` `→` [full](https://solscan.io/account/AyjCrA7rMZVDC6XLCbFRamLd7pxCbrfoPNttsQF13Fjp) | +42,488 | 1 |
| 6 | `6q8jdEAK...bxie` `→` [full](https://solscan.io/account/6q8jdEAKVVtXZaTZCWjMis6mR5SKp4S2vS3kMTcbbxie) | +27,245 | 1 |
| 7 | `8CHtrLZj...YJ8K` `→` [full](https://solscan.io/account/8CHtrLZjmy1WHis86VRkUqx3TkVeifAzakMou7D3YJ8K) | +26,925 | 1 |
| 8 | `GuEijmhQ...W5jt` `→` [full](https://solscan.io/account/GuEijmhQ1vSBy9rPcGT3YqEHrFmCLNfoe7VBT6cHW5jt) | +26,583 | 1 |
| 9 | `7fXMJ4RD...J5Xv` `→` [full](https://solscan.io/account/7fXMJ4RDR7PyoTWK8hw3V26ixksawFnNT23b9Vk1J5Xv) | +19,145 | 1 |
| 10 | `GCtfm9ax...14pP` `→` [full](https://solscan.io/account/GCtfm9axoPDdnQDXevS5BfCRMsQsmwrqMhuXKB5g14pP) | +17,523 | 1 |


*Generated 2026-09-20T03:37:28Z. Full data in [dashboard.html](./dashboard.html).*

---

## ⚠️ Key Finding (Sep 20)

After analyzing **62 quality "smart money" tokens** (volume ≥ $10k, net buy ≥ $5k, swaps ≥ 1k), we found **903 unique winning wallets** but **0 of them won on more than one token**.

This strongly suggests the "smart money" on Pump.fun is **not repeat winners** — it's likely:
- 🎯 Coordinated insider groups per launch
- 🎯 Snipers with single-shot entries
- 🎯 Bundled liquidity provider rewards (one token, then move on)

**Implication:** Pure copy-trading is unlikely to work without insider-style information. The most consistent edge appears to be:
1. Being early on tokens with **smart-degen presence**
2. Tracking **token-specific** wallets (each token's bag of insiders)
3. **Avoiding** the late entry on tokens where smart money already exited

---

## 🚧 Investigation Timeline

1. **Top traders leaderboard (GMGN)** — found wallets but all high-frequency bots
2. **Smart-money tagged trades** — same issue
3. **Early buyers of tokens that pumped** — only one-shot snipers
4. **High-frequency filtering (<50/day)** — too many false positives
5. **Wash pattern detection (8 detectors)** — filtered some bots
6. **Bridge/aggregator detection** — filtered wallets
7. ✅ **Token-first discovery (62 quality tokens)** — found 903 wallets, top wins 83.2k SOL
