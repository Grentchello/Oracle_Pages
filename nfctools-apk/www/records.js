// Record builders for each Write tab record type. Each returns an array
// of NDEF record dicts (matching the NDEFReader.write signature).

import { ndefTextRecord, ndefUrlRecord, ndefMimeRecord } from "./nfc.js";

const esc = (s) => String(s ?? "").trim();

export function buildRecords(type, fields) {
  switch (type) {
    case "url":
      return [ndefUrlRecord(esc(fields.value))];
    case "text":
      return [ndefTextRecord(esc(fields.value), esc(fields.lang || "en"))];
    case "email":
      // mailto: URI
      return [ndefUrlRecord("mailto:" + esc(fields.value))];
    case "tel":
      return [ndefUrlRecord("tel:" + esc(fields.value).replace(/[^\d+]/g, ""))];
    case "sms": {
      const num = esc(fields.number).replace(/[^\d+]/g, "");
      const body = esc(fields.body);
      return [ndefUrlRecord(`sms:${num}?body=${encodeURIComponent(body)}`)];
    }
    case "geo": {
      const lat = Number(fields.lat);
      const lon = Number(fields.lon);
      if (!isFinite(lat) || !isFinite(lon)) throw new Error("Latitude/longitude must be numbers");
      return [ndefUrlRecord(`geo:${lat},${lon}`)];
    }
    case "wifi":
      return [buildWifiRecord(fields)];
    case "vcard":
      return [buildVCardRecord(fields)];
    case "json":
      return [buildJsonRecord(fields)];
    default:
      throw new Error("Unknown record type: " + type);
  }
}

function buildWifiRecord(f) {
  // WiFi credential record per Wi-Fi Alliance "WPA" config spec.
  // Encoded as a TLV blob inside a MIME media type "application/vnd.wfa.wsc".
  // Layout (big-endian):
  //   0x10 (Credential Type) + len(2) + 0x1002 + 0x0020 (Network Index)
  //   0x10 + len(2) + 0x1003 + 0x0001 (SSID)
  //   0x10 + len(2) + 0x100F (Auth Type) + 0x000X (WPA=0x0002, WEP=0x0001, nopass=0x0004)
  //   0x10 + len(2) + 0x1010 (Encryption) 0x0008 (AES) or 0x0001 (none)
  //   0x10 + len(2) + 0x1011 (Network Key = password)
  //   0x10 + len(2) + 0x1027 (Hidden) + bool
  //   0x10 + len(2) + 0x104A (MAC)
  const ssid = enc(f.ssid);
  const pwd  = enc(f.password);
  const authType = f.auth === "WEP" ? 0x0001 : f.auth === "nopass" ? 0x0004 : 0x0002;
  const encType  = f.auth === "nopass" ? 0x0001 : 0x0008;

  const buf = [];
  push(buf, 0x1002, u16(0x0020));          // Network Index (often 1)
  push(buf, 0x1003, ssid);                  // SSID
  push(buf, 0x100F, u16(authType));         // Auth Type
  push(buf, 0x1010, u16(encType));          // Encryption
  if (f.auth !== "nopass") push(buf, 0x1011, pwd); // Network Key
  if (f.hidden) push(buf, 0x1027, [0x01]);

  return ndefMimeRecord("application/vnd.wfa.wsc", new Uint8Array(buf));
}

function buildVCardRecord(f) {
  const lines = [
    "BEGIN:VCARD",
    "VERSION:3.0",
    `FN:${esc(f.name)}`,
    `N:${esc(f.name).split(" ").reverse().join(";")};;;`,
  ];
  if (f.org)   lines.push(`ORG:${esc(f.org)}`);
  if (f.title) lines.push(`TITLE:${esc(f.title)}`);
  if (f.tel)   lines.push(`TEL;TYPE=WORK,VOICE:${esc(f.tel)}`);
  if (f.email) lines.push(`EMAIL;TYPE=WORK,INTERNET:${esc(f.email)}`);
  if (f.url)   lines.push(`URL:${esc(f.url)}`);
  if (f.addr)  lines.push(`ADR;TYPE=WORK:;;${esc(f.addr)};;;;`);
  if (f.note)  lines.push(`NOTE:${esc(f.note)}`);
  lines.push("END:VCARD");
  return ndefMimeRecord("text/vcard", lines.join("\r\n"));
}

function buildJsonRecord(f) {
  const mime = (f.mime || "application/json").trim() || "application/json";
  let text = f.json;
  // Validate JSON so the user catches errors before they tap a tag.
  try { JSON.parse(text); }
  catch (e) { throw new Error("JSON is not valid: " + e.message); }
  return ndefMimeRecord(mime, text);
}

function enc(s) { return new TextEncoder().encode(esc(s)); }
function u16(n) { return [(n >> 8) & 0xff, n & 0xff]; }

function push(buf, tagId, payload) {
  // Each attribute: tagId (u16 LE in spec? actually BE for WSC), len (u16 LE), payload.
  // The Wi-Fi Alliance spec uses little-endian for length, big-endian for IDs.
  const bytes = payload instanceof Uint8Array ? Array.from(payload) : Array.from(payload);
  const len = bytes.length;
  buf.push((tagId >> 8) & 0xff, tagId & 0xff);
  buf.push(len & 0xff, (len >> 8) & 0xff);
  for (const b of bytes) buf.push(b);
}

// Decode helpers for the read view.
export function describeRecord(rec) {
  const t = rec.recordType;
  const data = rec.data instanceof ArrayBuffer ? new Uint8Array(rec.data) : new Uint8Array(rec.data || []);
  if (t === "text") {
    const langLen = data[0] || 0;
    const lang = new TextDecoder().decode(data.slice(1, 1 + langLen));
    const text = new TextDecoder().decode(data.slice(1 + langLen));
    return { kind: "Text", label: lang, body: text };
  }
  if (t === "url" || t === "absolute-url") {
    return { kind: "URL", body: new TextDecoder().decode(data) };
  }
  if (t === "mime") {
    const mime = rec.mediaType || "application/octet-stream";
    let body = data;
    try { body = new TextDecoder("utf-8", { fatal: false }).decode(data); } catch {}
    return { kind: "MIME", label: mime, body, raw: data };
  }
  if (t === "smart-poster") {
    return { kind: "Smart Poster", body: new TextDecoder("utf-8", { fatal: false }).decode(data) };
  }
  if (t === "empty") return { kind: "(empty)" };
  return { kind: t, body: data, hex: toHex(data) };
}

export function toHex(bytes) {
  if (!bytes) return "";
  return Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join(" ");
}
