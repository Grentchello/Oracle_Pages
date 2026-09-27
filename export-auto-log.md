# Auto-Log Skill for Multica

This is the auto-log skill adapted for use with Multica. It handles:
- Daily wiki entries
- log.md append
- Git push to GitHub

## Files Needed

### SKILL.md

```markdown
---
name: auto-log
description: "Auto-log every session: wiki entries + daily note + log.md append + git push."
version: 1.0.1
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [workflow, journaling, daily-note, wiki, log, auto-log, meta]
    category: productivity
---

# Auto-Log

## What This Does
- Creates daily wiki entries in wiki/daily/YYYY-MM-DD.md
- Appends to wiki/log.md
- Git commits and pushes to GitHub

## Workflow

### Step 1 — Daily Note
```python
from datetime import datetime, timezone

wiki = "/opt/data/hermes_work/wiki"
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
note_path = f"{wiki}/daily/{today}.md"
```

### Step 2 — Append to Daily Note
```python
# Add entry to Done section
```

### Step 3 — Append to log.md
```markdown
## [YYYY-MM-DD] <action> | <subject>
- <bullet>
```

### Step 4 — Git Push
```bash
cd /opt/data/hermes_work
git add -A
git commit -m "<summary>"
git push origin main
```

## Configuration
- Wiki path: /opt/data/hermes_work/wiki
- Git remote: https://github.com/Grentchello/oracle_Vault
- PAT stored at: ~/.config/hermes/.git_token (Contents: Read+Write + workflow)

### Required Environment
- GIT_TOKEN or ~/.config/hermes/.git_token
- WIKI_PATH (default: /opt/data/hermes_work/wiki)
