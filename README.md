# Walls APK build source

This repo hosts the source code used to build the **Walls** Android app via GitHub Actions.

The app fetches wallpapers from the public repo [harilvfs/androidwallpapers](https://github.com/harilvfs/androidwallpapers)
(Unlicense / public domain). The APK itself is small (~3 MB) and ships only a manifest
of URLs; wallpapers stream from GitHub at runtime.

## What's inside

- `walls-app/` — Capacitor source (web app + Android shell)
- `walls-app/www/` — the actual HTML/CSS/JS
- `walls-app/www/manifest.json` — list of all 435 wallpapers, regenerated from the upstream repo
- `.github/workflows/build-walls.yml` — workflow that builds the APK on `ubuntu-latest`

## Build

Pushes to this repo's `main` branch trigger a build. Download the APK from the
[Actions](../../actions) tab as `walls-debug-apk`.

## Regenerate the manifest

The `manifest.json` was generated from the upstream tree API. To refresh:

```bash
curl -s 'https://api.github.com/repos/harilvfs/androidwallpapers/git/trees/main?recursive=1' | \
  python3 -c "...see notes..."
```
