---
title: NFC Tools
---

# NFC Tools

A simple read/write app for NDEF NFC tags. Runs in any Android Chrome browser.

[Open NFC Tools →](https://nfctools.duckdns.org/){ .md-button .md-button--primary }

## What it does

- **Read** any NDEF tag — shows the records (URL, text, WiFi, vCard, custom MIME), serial number, and raw bytes
- **Write** these record types:
    - URL (open a website on tap)
    - Plain text
    - WiFi credentials (WPA/WPA2/WEP/open, hidden SSID support)
    - vCard 3.0 contact cards
    - Email (`mailto:`)
    - Phone (`tel:`)
    - SMS pre-filled (`sms:number?body=...`)
    - Geo location (`geo:lat,lon`)
    - Custom JSON with arbitrary MIME type
- **Erase** tags (writes a single empty NDEF record, blanks the tag for most readers)
- **History** of every read/write/erase, stored locally in `localStorage`. Export as JSON.

## How it works

Pure web app. Uses the [Web NFC API](https://web.dev/articles/nfc) — no app install, no native bridge. Open the URL, tap the action, tap your phone against an NFC tag.

**Requirements:**

- Android phone with Chrome 89+ (any browser that supports Web NFC — currently Android Chrome and a few others)
- HTTPS — Web NFC requires a secure context
- A user gesture (button click) to start a read or write

**Limitations:**

- iOS Safari doesn't support Web NFC (Apple hasn't shipped it). The app will load and show "NFC unavailable" — no error.
- Can't lock tags permanently from a browser (that requires a native app with raw NFC commands).
- Mifare Classic tags without NDEF formatting, and some ISO 14443-4 cards, may not be readable.

## Files

The app is a small static site:

| File | What |
| --- | --- |
| `index.html` | Layout and tabs |
| `styles.css` | Dark theme, mobile-first |
| `nfc.js` | Thin wrapper over the `NDEFReader` API |
| `records.js` | Builders for each record type (URL, WiFi, vCard, etc.) + read-side decoders |
| `app.js` | Tab switching, scan/write/erase logic, history persistence |
| `manifest.webmanifest` | PWA manifest (install to home screen) |
| `icon.svg` | App icon |

Source lives at `/opt/data/hermes_work/nfctools/` on the Hermes container.

## Privacy

Everything runs in your browser. No tag data is sent to any server. History is in `localStorage` on your device only.

## Status

v1.0 — working. Needs to be deployed on a public HTTPS URL (currently running locally on the Hermes container for testing).
