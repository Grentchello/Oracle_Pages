# Oracle_Pages

Public dashboard for [Grentchello/oracle_Vault](https://github.com/Grentchello/oracle_Vault).

This repo is the **output target** for GitHub Pages. The actual content lives in
the private `oracle_Vault` repo. A GitHub Action in this repo:

1. Pulls `wiki/` from `oracle_Vault` (via the `ORACLE_VAULT_PAT` secret)
2. Builds it with MkDocs Material
3. Deploys to GitHub Pages at **https://grentchello.github.io/Oracle_Pages/**

No edits happen here — all updates flow from `oracle_Vault`.
<!-- trigger build -->



<!-- refresh -->

<!-- trigger deploy -->
