// Main app: tab switching, scan UI, write UI, history, persistence.

import { isSupported, scan, stop, write } from "./nfc.js";
import { buildRecords, describeRecord, toHex } from "./records.js";

const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => Array.from(root.querySelectorAll(s));

const els = {
  conn: $("#conn"),
  tabs: $$(".tab"),
  panels: $$(".panel"),
  // read
  btnScan: $("#btn-scan"),
  btnStopScan: $("#btn-stop-scan"),
  readStatus: $("#read-status"),
  readResult: $("#read-result"),
  // write
  writeType: $("#write-type"),
  fValue: $("#f-value"),
  writePreview: $("#write-preview"),
  btnWrite: $("#btn-write"),
  btnWriteCancel: $("#btn-write-cancel"),
  writeStatus: $("#write-status"),
  // erase
  btnErase: $("#btn-erase"),
  btnEraseCancel: $("#btn-erase-cancel"),
  eraseStatus: $("#erase-status"),
  // history
  historyList: $("#history-list"),
  btnClearHistory: $("#btn-clear-history"),
  btnExportHistory: $("#btn-export-history"),
  // toast
  toast: $("#toast"),
};

const state = {
  reading: false,
  writing: false,
};

// --- Tabs ---
els.tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    els.tabs.forEach(t => { t.classList.toggle("active", t === tab); t.setAttribute("aria-selected", t === tab); });
    const id = tab.dataset.tab;
    els.panels.forEach(p => {
      const on = p.id === `tab-${id}`;
      p.classList.toggle("active", on);
      p.hidden = !on;
    });
    // Stop any active scan/writes when leaving a tab.
    if (id !== "read" && state.reading) doStopScan();
    if (id !== "write" && state.writing) cancelWrite();
  });
});

// --- Connection status ---
if (isSupported()) {
  els.conn.textContent = "NFC ready";
  els.conn.classList.add("ok");
} else {
  els.conn.textContent = "NFC unavailable";
  els.conn.classList.add("bad");
  els.btnScan.disabled = true;
  els.btnWrite.disabled = true;
  els.btnErase.disabled = true;
}

// --- Read ---
els.btnScan.addEventListener("click", doScan);
els.btnStopScan.addEventListener("click", doStopScan);

async function doScan() {
  if (!isSupported()) return;
  els.btnScan.disabled = true;
  els.btnStopScan.disabled = false;
  state.reading = true;
  setStatus(els.readStatus, "Waiting for a tag…", "");
  els.readResult.hidden = true;

  try {
    await scan({
      onReading: (e) => {
        setStatus(els.readStatus, "Tag detected", "ok");
        renderRead(e);
        addHistory("read", e);
      },
      onError: (err) => {
        setStatus(els.readStatus, err.message, "bad");
      },
    });
  } catch (err) {
    setStatus(els.readStatus, err.message, "bad");
    state.reading = false;
    els.btnScan.disabled = false;
    els.btnStopScan.disabled = true;
  }
}

function doStopScan() {
  stop();
  state.reading = false;
  els.btnScan.disabled = false;
  els.btnStopScan.disabled = true;
  if (els.readStatus.textContent.startsWith("Waiting")) {
    setStatus(els.readStatus, "Scan stopped", "warn");
  }
}

function renderRead({ serialNumber, records }) {
  const root = els.readResult;
  root.innerHTML = "";
  root.hidden = false;

  const meta = document.createElement("div");
  meta.className = "meta";
  meta.innerHTML = `
    <span>${records.length} record${records.length === 1 ? "" : "s"}</span>
    ${serialNumber ? `<span>UID: ${escapeHtml(serialNumber)}</span>` : ""}
  `;
  root.appendChild(meta);

  if (records.length === 0) {
    const p = document.createElement("p");
    p.textContent = "Empty tag (no NDEF records).";
    root.appendChild(p);
    return;
  }

  const list = document.createElement("div");
  list.className = "records";
  for (const rec of records) {
    const d = describeRecord(rec);
    const div = document.createElement("div");
    div.className = "record";
    div.innerHTML = `
      <div class="rtype">${escapeHtml(d.kind)}${d.label ? ` · ${escapeHtml(d.label)}` : ""}</div>
      <div class="rdata">${escapeHtml(d.body)}</div>
    `;
    // Open URLs in a new tab.
    if (d.kind === "URL" || d.kind === "Smart Poster") {
      const a = document.createElement("a");
      a.href = d.body;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = "Open link";
      const actions = document.createElement("div");
      actions.className = "raction";
      actions.appendChild(a);
      div.appendChild(actions);
    }
    list.appendChild(div);
  }
  root.appendChild(list);

  // Raw hex of all records concatenated (best-effort preview).
  const totalBytes = records.reduce((sum, r) => {
    const d = r.data instanceof ArrayBuffer ? new Uint8Array(r.data) : new Uint8Array(r.data || []);
    return sum + d.length;
  }, 0);
  if (totalBytes > 0) {
    const hex = document.createElement("div");
    hex.className = "hex";
    hex.textContent = "Raw bytes (first 256):\n" + toHex(records[0].data instanceof ArrayBuffer ? new Uint8Array(records[0].data).slice(0, 256) : new Uint8Array(records[0].data || []).slice(0, 256));
    root.appendChild(hex);
  }
}

// --- Write ---
function updateWriteForm() {
  const type = els.writeType.value;
  $$('[data-record]', $('.form')).forEach(el => {
    const types = el.dataset.record.split(/\s+/);
    el.hidden = !types.includes(type);
  });
  refreshPreview();
}

['change', 'input'].forEach(ev => {
  els.writeType.addEventListener(ev, updateWriteForm);
  $('.form').addEventListener(ev, refreshPreview);
});

function readFormFields() {
  const t = els.writeType.value;
  const f = { value: els.fValue.value.trim() };
  if (t === "text")   f.lang = $("#f-text-lang").value.trim();
  if (t === "wifi") { f.ssid = $("#f-wifi-ssid").value; f.password = $("#f-wifi-pass").value; f.auth = $("#f-wifi-auth").value; f.hidden = $("#f-wifi-hidden").checked; }
  if (t === "vcard") { f.name = $("#f-vc-name").value; f.org = $("#f-vc-org").value; f.title = $("#f-vc-title").value; f.tel = $("#f-vc-tel").value; f.email = $("#f-vc-email").value; f.url = $("#f-vc-url").value; f.addr = $("#f-vc-addr").value; f.note = $("#f-vc-note").value; }
  if (t === "sms")   { f.number = $("#f-sms-number").value; f.body = $("#f-sms-body").value; }
  if (t === "geo")   { f.lat = $("#f-geo-lat").value; f.lon = $("#f-geo-lon").value; }
  if (t === "json")  { f.json = $("#f-json").value; f.mime = $("#f-json-mime").value; }
  return f;
}

function refreshPreview() {
  const t = els.writeType.value;
  try {
    const records = buildRecords(t, readFormFields());
    const lines = [];
    for (const r of records) {
      let payload = r.data;
      if (payload instanceof Uint8Array) {
        try { payload = new TextDecoder("utf-8", { fatal: false }).decode(payload); } catch {}
      }
      const head = r.mediaType ? `[mime ${r.mediaType}] ` : `[${r.recordType}] `;
      const body = typeof payload === "string"
        ? payload
        : `(binary, ${payload?.length || 0} bytes)`;
      lines.push(head + body);
    }
    els.writePreview.textContent = lines.join("\n");
    els.btnWrite.disabled = false;
  } catch (e) {
    els.writePreview.textContent = "⚠ " + e.message;
    els.btnWrite.disabled = true;
  }
}

els.btnWrite.addEventListener("click", doWrite);
els.btnWriteCancel.addEventListener("click", cancelWrite);

async function doWrite() {
  if (!isSupported()) return;
  const t = els.writeType.value;
  let records;
  try { records = buildRecords(t, readFormFields()); }
  catch (e) { setStatus(els.writeStatus, e.message, "bad"); return; }

  state.writing = true;
  els.btnWrite.disabled = true;
  els.btnWriteCancel.hidden = false;
  setStatus(els.writeStatus, "Tap a tag to write…", "");

  try {
    await write(records, {
      onRead: (e) => {
        setStatus(els.writeStatus, "Tag detected, writing…", "");
        renderRead(e);
      },
    });
    setStatus(els.writeStatus, "Write successful", "ok");
    addHistory("write", { type: t, records: [{ recordType: records[0].recordType, data: records[0].data, mediaType: records[0].mediaType }] });
    toast("Tag written");
  } catch (err) {
    if (err.name === "AbortError") {
      setStatus(els.writeStatus, "Write cancelled", "warn");
    } else {
      setStatus(els.writeStatus, "Write failed: " + err.message, "bad");
      addHistory("write-fail", { error: err.message });
    }
  } finally {
    state.writing = false;
    els.btnWrite.disabled = false;
    els.btnWriteCancel.hidden = true;
  }
}

function cancelWrite() {
  // The NDEFReader's `write` is hard to abort mid-call; we just mark it
  // and the user can move the tag away to trigger a 'NotAllowedError'.
  // For long writes the OS will time out on its own.
  setStatus(els.writeStatus, "Move the tag away to cancel", "warn");
}

// --- Erase ---
els.btnErase.addEventListener("click", doErase);
els.btnEraseCancel.addEventListener("click", () => { state.erasing = false; els.btnEraseCancel.hidden = true; });

async function doErase() {
  if (!isSupported()) return;
  state.erasing = true;
  els.btnErase.disabled = true;
  els.btnEraseCancel.hidden = false;
  setStatus(els.eraseStatus, "Tap a tag to erase…", "");
  try {
    // An "empty" NDEF record on a tag effectively blanks it for most readers.
    await write([{ recordType: "empty" }]);
    setStatus(els.eraseStatus, "Tag erased", "ok");
    addHistory("erase", { ok: true });
    toast("Tag erased");
  } catch (err) {
    setStatus(els.eraseStatus, "Erase failed: " + err.message, "bad");
  } finally {
    state.erasing = false;
    els.btnErase.disabled = false;
    els.btnEraseCancel.hidden = true;
  }
}

// --- History ---
const HIST_KEY = "nfctools.history";
function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HIST_KEY) || "[]"); } catch { return []; }
}
function saveHistory(h) { localStorage.setItem(HIST_KEY, JSON.stringify(h.slice(0, 200))); }
function addHistory(kind, payload) {
  const h = loadHistory();
  h.unshift({ ts: Date.now(), kind, payload });
  saveHistory(h);
  renderHistory();
}
function renderHistory() {
  const h = loadHistory();
  els.historyList.innerHTML = h.length ? "" : '<p class="hint">No history yet.</p>';
  for (const item of h) {
    const div = document.createElement("div");
    div.className = "history-item h' + (item.kind === "read" ? "read" : item.kind.includes("fail") ? "bad" : "ok");
    const when = new Date(item.ts).toLocaleString();
    let body = "";
    if (item.kind === "read") {
      const r = item.payload.records[0];
      if (r) {
        const d = describeRecord(r);
        body = `<b>${escapeHtml(d.kind)}</b>: ${escapeHtml(typeof d.body === "string" ? d.body : `(${d.body?.length || 0} bytes)`)}`;
      } else {
        body = "(empty tag)";
      }
    } else if (item.kind === "write") {
      body = `Wrote <b>${escapeHtml(item.payload.type)}</b> record`;
    } else if (item.kind === "erase") {
      body = "Erased";
    } else if (item.kind === "write-fail") {
      body = `Write failed: ${escapeHtml(item.payload.error)}`;
    }
    div.innerHTML = `<div class="hwhen">${escapeHtml(when)} · ${escapeHtml(item.kind)}</div><div class="hbody">${body}</div>`;
    els.historyList.appendChild(div);
  }
}
els.btnClearHistory.addEventListener("click", () => { localStorage.removeItem(HIST_KEY); renderHistory(); });
els.btnExportHistory.addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(loadHistory(), null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "nfc-history.json"; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

// --- Toast ---
let toastTimer = null;
function toast(msg) {
  els.toast.textContent = msg;
  els.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { els.toast.hidden = true; }, 2500);
}

function setStatus(el, msg, kind) {
  el.hidden = false;
  el.textContent = msg;
  el.classList.remove("ok", "bad", "warn");
  if (kind) el.classList.add(kind);
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Init
updateWriteForm();
renderHistory();
