---
title: oracle_Vault — Master Dashboard
---

# oracle_Vault

> Grant's personal knowledge vault and project dashboard.
> Mobile-friendly. Auto-deploys from GitHub on every push.

[Open in GitHub :fontawesome-brands-github:](https://github.com/Grentchello/oracle_Vault){ .md-button }

---

## Projects

<div class="grid cards" markdown>

-   :material-rocket-launch: **[Memecoin Trading Bot (Solana)](projects/memecoin-trading/index.md)**

    ---

    **Status:** v9.3 live. Solana chain, 60s ticks, GMGN fragility gate.

    Paper trading memecoins on Solana with ME2F fragility scoring,
    slippage simulation, and ghost exits for rugs.

-   :material-rocket-launch: **[Base Memecoin Trading](projects/base-memecoin/dashboard.html)**

    ---

    **Status:** v1.0 live. Base chain (Coinbase L2), 60s ticks, 0.1 ETH.

    Autonomous paper trading of Base chain memecoins via DexPaprika
    and DexScreener. Different dashboard, different strategy.

    [🔵 Open Base Dashboard →](projects/base-memecoin/dashboard.html){ .md-button }

-   :material-rocket-launch: **[Trading Pairs Bot](projects/trading-pairs/index.md)**

    ---

    **Status:** v1 running. 6 pairs × 4 strategies, paper $1000 bankroll.

-   :material-magnify: **[Copy-Trading Wallets](projects/copy-trading/index.md)**

    ---

    **Status:** v1 live. 22 Solana traders found, 60d proxy score.

    Smart-money wallet discovery via GMGN with anti-copier wash filters
    (bundlers, snipe bots, instant roundtrips, sell traps).

-   :material-folder-open: **[Browse all projects](projects/index.md)**

    ---

    Every project Hermes builds lives in its own sub-dashboard. Click into any
    one for notes, status, and links.

-   :material-check-circle: **[Tasks](tasks/index.md)**

    ---

    Private todo list. Password-protected. Updated via chat with Hermes.

</div>

---

## Recent activity

The latest daily journal entry:

- **[Daily — 2026-08-25](daily/2026-08-25.md)** — Vault bootstrap, auto-log skill, MkDocs master dashboard

## Live systems

- ✅ **[Tasks](tasks/index.md)** — private todo list (password-protected)
- 🟢 **[Memecoin Trading Dashboard](trading/index.html)** — ACTIVE (v8.3 conservative mode, CoinCLIP + ME2F + GMGN fragility gates)
- 📊 **[Trading Pairs Bot](projects/trading-pairs/index.md)** — multi-pair multi-strategy (SUPER/ROC/BB/DIR) on BTC/ETH/SOL/BNB/XRP/ARB
- 🖼️ **[Wallpapers](_meta/wallpapers.md)** — phone wallpapers scraped from [alisonfriend.com](https://alisonfriend.com/) (36 images, iPhone + Android sizes)
- **[Workflow docs →](_meta/method.md)**
- 🐳 **[Coolify](http://207.211.145.179:8000/)** — self-hosted PaaS for deploying services (this machine, port 8000)

See the [full daily journal](daily/index.md) for everything.

---

## 🐳 Coolify (Self-Hosted PaaS)

Self-hosted PaaS running on this machine. Deploy apps, databases, and services with Docker:

[Open Coolify →](http://207.211.145.179:8000/){ .md-button .md-button--primary }

**What it does:** Coolify lets you deploy services from GitHub repos with one click. Alternative to Heroku/Vercel but self-hosted on your own hardware. Currently hosts the FCC proxy, image generator tunnels, and any other apps we spin up.

**Status:** Live on `http://207.211.145.179:8000/` (this machine's public IP, port 8000). Direct HTTP access (not tunneled).

---

## Free Claude Code (FCC)

Admin UI for configuring free LLM providers (OpenAI, Claude, Hermes, Gemini, etc.):

[Open FCC Admin →](https://rugby-answer-computation-occur.trycloudflare.com/admin){ .md-button .md-button--primary }

**What it does:** Free Claude Code proxies 50+ LLM providers through a local server. When Hermes runs out of MiniMax tokens, it automatically falls back to FCC for free models (OpenCode Zen, GLM, etc.).

**Status:** `opencode_zen/mimo-v2.5-free` active. No auth required. Ephemeral URL (restarting the tunnel gives a new URL).

---

## 🔮 Image Generator

[Open Image Generator →](https://incoming-cowboy-crop-and.trycloudflare.com){ .md-button .md-button--primary }

**What it does:** Enter a prompt, get an image. Two modes:

**⚡ Fast mode (default)** — Pollinations AI cloud (2-10 sec)

**🎨 Local SD 1.5** — Runs on this server CPU (15-30 min, free, private)

**How it works:**

1. Choose mode (Fast recommended)
2. Type your prompt
3. Click **Generate** — image appears
4. Click to zoom, download to save

**Features:** Progress bar, generation history, gallery of all outputs

[View All Generated Images →](https://incoming-cowboy-crop-and.trycloudflare.com/gallery){ .md-button }





<!-- v2 -->
<!-- trigger Mon Sep 14 06:06:20 UTC 2026 -->

