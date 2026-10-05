// Web NFC wrapper: thin layer over the NDEFReader API.

let activeReader = null;

export function isSupported() {
  return typeof window !== "undefined" && "NDEFReader" in window;
}

export async function scan({ onReading, onError } = {}) {
  if (!isSupported()) throw new Error("Web NFC is not available in this browser");
  if (activeReader) throw new Error("A scan is already active");

  const reader = new NDEFReader();
  activeReader = reader;

  reader.addEventListener("reading", (event) => {
    onReading?.({
      serialNumber: event.serialNumber || "",
      records: Array.from(event.message.records || []),
    });
  });
  reader.addEventListener("readingerror", (event) => {
    onError?.(new Error("Read error: " + (event.message || "tag could not be parsed")));
  });

  await reader.scan({ signal: makeAbortController().signal });
  return () => stop();
}

let _controller = null;
function makeAbortController() {
  _controller = new AbortController();
  return _controller;
}

export function stop() {
  try { _controller?.abort(); } catch {}
  _controller = null;
  activeReader = null;
}

export async function write(records, { signal, onRead } = {}) {
  if (!isSupported()) throw new Error("Web NFC is not available in this browser");
  const reader = new NDEFReader();
  // Web NFC write needs a tag present. We await the `reading` event to know
  // a tag was found; if `onRead` is provided we report that to the caller.
  if (onRead) {
    reader.addEventListener("reading", (event) => {
      onRead({
        serialNumber: event.serialNumber || "",
        records: Array.from(event.message.records || []),
      });
    });
  }
  // `reader.write` resolves when the write is committed.
  return reader.write({ records, signal });
}

// Helpers to build NDEF record dictionaries for the NDEFReader.
export const rtd = {
  url: "url",
  text: "text",
  mime: "mime",
  wifi: new Uint8Array([0x03]),       // Mime("application/vnd.wfa.wsc") for WiFi (we use the MIME form below)
  vcard: new Uint8Array([0x03]),      // vCard via MIME text/vcard
};

export function ndefTextRecord(text, lang = "en") {
  const langBytes = new TextEncoder().encode(lang);
  const textBytes = new TextEncoder().encode(text);
  const payload = new Uint8Array(langBytes.length + 1 + textBytes.length);
  payload[0] = langBytes.length;
  payload.set(langBytes, 1);
  payload.set(textBytes, 1 + langBytes.length);
  return { recordType: "text", data: payload };
}

export function ndefUrlRecord(url) {
  return { recordType: "url", data: new TextEncoder().encode(url) };
}

export function ndefMimeRecord(mime, data) {
  let bytes;
  if (typeof data === "string") bytes = new TextEncoder().encode(data);
  else if (data instanceof Uint8Array) bytes = data;
  else bytes = new Uint8Array(0);
  return { recordType: "mime", mediaType: mime, data: bytes };
}

export function ndefSmartPoster(url, title) {
  // Minimal Smart Poster: type 'sp' with a payload of well-known URI + title (Act/Cnt/Title optional, omitted here).
  return { recordType: "smart-poster", data: new TextEncoder().encode(url) };
}
