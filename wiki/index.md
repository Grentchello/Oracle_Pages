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

-   :material-rocket-launch: **[Memecoin Trading Bot](projects/memecoin-trading/index.md)**

    ---

    **Status:** planning — research & design phase

    Autonomous memecoin trading bot. Ground zero: deciding on chain, strategy,
    and infrastructure before any code.

-   :material-rocket-launch: **[Trading Pairs Bot](projects/trading-pairs/index.md)**

    ---

    **Status:** v1 running. 6 pairs × 4 strategies, paper $1000 bankroll.

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

See the [full daily journal](daily/index.md) for everything.

---

## Free Claude Code (FCC)

Admin UI for configuring free LLM providers (OpenAI, Claude, Hermes, Gemini, etc.):

[Open FCC Admin →](https://rugby-answer-computation-occur.trycloudflare.com/admin){ .md-button .md-button--primary }

**What it does:** Free Claude Code proxies 50+ LLM providers through a local server. When Hermes runs out of MiniMax tokens, it automatically falls back to FCC for free models (OpenCode Zen, GLM, etc.).

**Status:** `opencode_zen/mimo-v2.5-free` active. No auth required. Ephemeral URL (restarting the tunnel gives a new URL).

---

## 🔮 Image Generator

[Open Image Generator →](https://incoming-cowboy-crop-and.trycloudflare.com){ .md-button .md-button--primary }

**What it does:** Pick a workflow, enter a prompt, ComfyUI auto-starts → generates image → shuts down to save RAM.

**Model:** FLUX.2 Klein 4B (GGUF Q8_0, 4 GB) on CPU · Qwen3-4B text encoder · ~2-5 min per image

**How it works:**

1. Click **Start** (or it auto-starts when you generate)
2. Type your prompt
3. Click **Generate** — ComfyUI boots, runs the job, shows the image
4. ComfyUI auto-stops after 5 min idle to free ~8 GB RAM

**Features:** Progress bar, generation history, auto lifecycle management

[View All Generated Images →](https://incoming-cowboy-crop-and.trycloudflare.com/gallery){ .md-button }
