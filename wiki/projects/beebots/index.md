---
title: Beebots — AI Trading Bees
---

# Beebots 🐝

AI trading bees racing on OKX perpetual futures. Three bees make trading decisions using Jev (TypeSafe AI's decision model), with a risk layer written in plain code.

## Status

- **Deployment:** Coolify (port 3000 via cloudflared)
- **Mode:** Paper trading (default)
- **Setup:** Needs API keys to complete

## Links

- [GitHub](https://github.com/imikerussell/beebots)
- [Live Dashboard](https://career-mapping-recall-magnitude.trycloudflare.com)
- [The Hive Leaderboard](https://beebots.tech)

## Setup Required

To complete setup, add these to `.env`:

```
TYPESAFE_API_KEY=<from https://console.typesafe.ai/keys>
OPENAI_API_KEY=<from OpenAI>
```

## Architecture

- **Engine:** ghcr.io/imikerussell/beebots-engine:latest
- **Web:** ghcr.io/imikerussell/beebots-web:latest (Caddy reverse proxy)
- **Backup:** ghcr.io/imikerussell/beebots-backup:latest

## How It Works

1. Each bee gets $333 paper money
2. Every 10 seconds (configurable), each bee asks Jev for a trading decision
3. Orders go through a risk layer before execution
4. All decisions, orders, fees, and funding payments appear on the dashboard in real-time
