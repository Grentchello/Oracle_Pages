---
title: Projects
---

# Projects

> Each project gets its own sub-dashboard. Click into any for the full notes,
> status, and linked resources.

---

## Active projects

<div class="grid cards" markdown>

-   :material-rocket-launch: **[Memecoin Trading Bot](memecoin-trading/index.md)**

    ---

    **Planning** — ground zero.

    Autonomous trading bot for memecoins. Currently deciding on chain,
    strategy, and infrastructure.

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