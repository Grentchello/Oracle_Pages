// Walls — view and download wallpapers from harilvfs/androidwallpapers

const MANIFEST_URL = "./manifest.json";
const STORAGE_KEY = "walls_state_v1";

let walls = [];
let filtered = [];
let currentIndex = -1;
let currentBlob = null; // for "set as wallpaper"

const grid = document.getElementById("grid");
const search = document.getElementById("search");
const stats = document.getElementById("stats");
const lightbox = document.getElementById("lightbox");
const lbImg = document.getElementById("lbImg");
const lbName = document.getElementById("lbName");
const lbSize = document.getElementById("lbSize");
const lbStatus = document.getElementById("lbStatus");
const lbDownload = document.getElementById("lbDownload");
const lbWallpaper = document.getElementById("lbWallpaper");
const lbClose = document.getElementById("lbClose");
const lbPrev = document.getElementById("lbPrev");
const lbNext = document.getElementById("lbNext");
const toast = document.getElementById("toast");

function showToast(msg, duration = 2500) {
  toast.textContent = msg;
  toast.hidden = false;
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => { toast.hidden = true; }, duration);
}

function fmtSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1024 / 1024).toFixed(2) + " MB";
}

// Lazy load with IntersectionObserver
const io = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (e.isIntersecting) {
      const tile = e.target;
      const url = tile.dataset.url;
      const img = document.createElement("img");
      img.loading = "lazy";
      img.src = url;
      img.onload = () => tile.classList.remove("loading");
      img.onerror = () => {
        tile.classList.remove("loading");
        tile.style.background = "rgba(239,68,68,0.1)";
      };
      io.unobserve(tile);
    }
  }
}, { rootMargin: "200px" });

function render(list) {
  if (!list.length) {
    grid.innerHTML = `<div class="empty"><h3>No matches</h3><p>Try a different search.</p></div>`;
    return;
  }
  const frag = document.createDocumentFragment();
  for (const w of list) {
    const tile = document.createElement("div");
    tile.className = "tile loading";
    tile.dataset.url = w.thumbUrl;
    tile.dataset.name = w.name;
    tile.addEventListener("click", () => openLightbox(w));
    frag.appendChild(tile);
  }
  grid.innerHTML = "";
  grid.appendChild(frag);
  // Observe new tiles
  for (const tile of grid.querySelectorAll(".tile")) {
    io.observe(tile);
  }
}

function applyFilter() {
  const q = search.value.trim().toLowerCase();
  if (!q) {
    filtered = walls.slice();
  } else {
    filtered = walls.filter(w => w.name.toLowerCase().includes(q));
  }
  stats.textContent = `${filtered.length} of ${walls.length} wallpapers`;
  render(filtered);
}

async function loadManifest() {
  // Try localStorage cache first (offline-friendly)
  let cached = null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) cached = JSON.parse(raw);
  } catch (e) {}
  if (cached && cached.manifest && cached.manifest.walls) {
    walls = cached.manifest.walls;
    stats.textContent = `Loading ${walls.length} wallpapers…`;
    applyFilter();
  }
  try {
    const res = await fetch(MANIFEST_URL, { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const m = await res.json();
    walls = m.walls || [];
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ manifest: m })); } catch (e) {}
    applyFilter();
  } catch (e) {
    if (!cached) {
      grid.innerHTML = `<div class="empty"><h3>Couldn't load wallpapers</h3><p>${e.message}</p><p style="margin-top: 12px;">Are you online? Try again.</p></div>`;
    }
  }
}

function openLightbox(w) {
  currentIndex = filtered.findIndex(x => x.name === w.name);
  if (currentIndex === -1) return;
  showLightbox(w);
}

function showLightbox(w) {
  lbImg.src = w.url;
  lbImg.alt = w.name;
  lbName.textContent = w.name;
  lbSize.textContent = fmtSize(w.size);
  lbStatus.textContent = "";
  lbStatus.classList.remove("error");
  lbDownload.disabled = false;
  lbWallpaper.disabled = false;
  lbDownload.textContent = "⬇ Download";
  lightbox.hidden = false;
  document.body.style.overflow = "hidden";
}

function closeLightbox() {
  lightbox.hidden = true;
  document.body.style.overflow = "";
  currentBlob = null;
}

function navigate(dir) {
  if (currentIndex < 0) return;
  currentIndex = (currentIndex + dir + filtered.length) % filtered.length;
  showLightbox(filtered[currentIndex]);
}

async function downloadCurrent() {
  const w = filtered[currentIndex];
  if (!w) return;
  lbDownload.disabled = true;
  lbStatus.textContent = "Downloading…";
  lbStatus.classList.remove("error");
  try {
    const res = await fetch(w.url);
    if (!res.ok) throw new Error("HTTP " + res.status);
    const blob = await res.blob();
    const filename = w.name;

    // Try Capacitor Filesystem first (saves into Pictures/Walls/ so user can find it in Photos)
    if (window.Capacitor?.Plugins?.Filesystem) {
      try {
        const base64 = await blobToBase64(blob);
        const result = await window.Capacitor.Plugins.Filesystem.writeFile({
          path: `Pictures/Walls/${filename}`,
          data: base64,
          recursive: true,
        });
        // Notify the media scanner so it shows up in Photos
        try {
          await window.Capacitor.Plugins.Filesystem.getUri({ path: `Pictures/Walls/${filename}` });
        } catch (e) {}
        lbStatus.textContent = `✓ Saved to Pictures/Walls/${filename}`;
        lbStatus.classList.remove("error");
        showToast(`Saved to Pictures/Walls/${filename}`);
        currentBlob = blob;
        lbDownload.textContent = "✓ Saved";
        return;
      } catch (e) {
        console.warn("Filesystem save failed, falling back to browser download", e);
      }
    }

    // Fallback: browser download
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    lbStatus.textContent = "✓ Downloaded";
    lbStatus.classList.remove("error");
    showToast(`Downloaded ${filename}`);
  } catch (e) {
    lbStatus.textContent = "✗ " + e.message;
    lbStatus.classList.add("error");
    showToast("Download failed: " + e.message);
  } finally {
    lbDownload.disabled = false;
  }
}

async function setAsWallpaper() {
  const w = filtered[currentIndex];
  if (!w) return;
  lbWallpaper.disabled = true;
  lbStatus.textContent = "Preparing…";
  lbStatus.classList.remove("error");
  try {
    // Get the bytes
    let blob = currentBlob;
    if (!blob) {
      const res = await fetch(w.url);
      blob = await res.blob();
      currentBlob = blob;
    }
    // On Android, opening the image in the system viewer lets them "Set as wallpaper"
    // via the share/menu. We can also use Capacitor's Browser plugin to open it.
    if (window.Capacitor?.Plugins?.Browser) {
      const base64 = await blobToBase64(blob);
      const result = await window.Capacitor.Plugins.Filesystem.writeFile({
        path: `Pictures/Walls/${w.name}`,
        data: base64,
        recursive: true,
      });
      // Open in system viewer using file:// or content:// uri
      try {
        await window.Capacitor.Plugins.Browser.open({ url: result.uri, presentationStyle: "fullscreen" });
        lbStatus.textContent = "Long-press the photo to set as wallpaper";
      } catch (e) {
        // Fallback: just save and tell user
        lbStatus.textContent = `✓ Saved — open ${w.name} from Photos to set as wallpaper`;
        showToast("Saved. Open from Photos and long-press to set wallpaper.");
      }
    } else {
      // Browser fallback: open the image URL in a new tab
      window.open(w.url, "_blank");
      lbStatus.textContent = "Opened — long-press the image to set as wallpaper";
    }
  } catch (e) {
    lbStatus.textContent = "✗ " + e.message;
    lbStatus.classList.add("error");
  } finally {
    lbWallpaper.disabled = false;
  }
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      // strip the data:image/jpeg;base64, prefix
      const result = reader.result;
      const idx = result.indexOf(",");
      resolve(idx >= 0 ? result.slice(idx + 1) : result);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

// Wire up events
search.addEventListener("input", applyFilter);
lbClose.addEventListener("click", closeLightbox);
lbPrev.addEventListener("click", () => navigate(-1));
lbNext.addEventListener("click", () => navigate(1));
lbDownload.addEventListener("click", downloadCurrent);
lbWallpaper.addEventListener("click", setAsWallpaper);

// Keyboard nav in lightbox
document.addEventListener("keydown", (e) => {
  if (lightbox.hidden) return;
  if (e.key === "Escape") closeLightbox();
  else if (e.key === "ArrowLeft") navigate(-1);
  else if (e.key === "ArrowRight") navigate(1);
});

// Swipe nav in lightbox
let touchStartX = 0;
lightbox.addEventListener("touchstart", (e) => {
  touchStartX = e.touches[0].clientX;
}, { passive: true });
lightbox.addEventListener("touchend", (e) => {
  const dx = e.changedTouches[0].clientX - touchStartX;
  if (Math.abs(dx) > 60) navigate(dx > 0 ? -1 : 1);
}, { passive: true });

// Shuffle button
document.getElementById("shuffle").addEventListener("click", () => {
  if (!filtered.length) return;
  for (let i = filtered.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [filtered[i], filtered[j]] = [filtered[j], filtered[i]];
  }
  render(filtered);
  showToast("Shuffled");
});

// Boot
loadManifest();