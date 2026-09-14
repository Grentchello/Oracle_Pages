---
title: Projects
---

# Projects

> Each project gets its own sub-dashboard. Click into any for the full notes,
> status, and linked resources.

---

## Active projects

<div class="grid cards" markdown>

-   :material-rocket-launch: **[Memecoin Trading Bot (Solana)](memecoin-trading/index.md)**

    ---

    **v9.3 live.** Solana chain, 60s ticks, GMGN fragility gate.

    Autonomous paper trading memecoins on Solana with ME2F fragility scoring,
    slippage simulation, and ghost exits for rugs.

-   :material-rocket-launch: **[Base Memecoin Trading](base-memecoin/index.md)**

    ---

    **v1.0 live.** Base chain (Coinbase L2), 60s ticks, 0.1 ETH.

    Autonomous paper trading of Base chain memecoins via DexPaprika and
    DexScreener. Different chain, different dashboard.

    [🔵 Open Live Dashboard →](base-memecoin/dashboard.html){ .md-button }

</div>

## How to start a new project

1. **Create a folder:** `projects/<project-name>/`
2. **Copy the template:**
    ```
    cp -r projects/_template/* projects/<project-name>/
    ```
3. **Edit `index.md`** to set the project name, summary, and status.
4. **Commit + push.** The dashboard updates on the next deploy.

See [`projects/_template/index.md`](_template/index.md) for the template itself
and what fields to fill in.

!!! note "Auto-discovery"
    Projects appear in the dashboard nav automatically once `index.md` exists
    in the project folder. If a new project is missing, add it to `mkdocs.yml`
    under the `Projects:` nav section.