// Car Launcher Pro Theme Pack - app.js
let themes = {};
let currentPreview = null;

const FONT_FAMILY = {
  futuristic: '"Courier New", monospace',
  warm: 'Georgia, serif',
  natural: '"Comic Sans MS", "Trebuchet MS", sans-serif',
  stormy: 'Arial, sans-serif',
};

async function loadThemes() {
  const res = await fetch('./themes/manifest.json');
  const manifest = await res.json();
  const grid = document.getElementById('themes-grid');
  grid.innerHTML = '';

  for (const [key, info] of Object.entries(manifest)) {
    const theme = await (await fetch(`./themes/${key}/theme.json`)).json();
    themes[key] = theme;
    const card = renderCard(key, theme);
    grid.appendChild(card);
  }
}

function renderCard(key, theme) {
  const card = document.createElement('div');
  card.className = 'theme-card';
  card.tabIndex = 0;
  card.setAttribute('data-theme', key);
  const c = theme.colors;
  card.innerHTML = `
    <div class="theme-preview" style="
      background: ${c.background};
      color: ${c.text};
      font-family: ${FONT_FAMILY[theme.style] || 'sans-serif'};
    ">
      <div class="clock" style="color: ${c.primary};">14:23</div>
      <div class="row">
        <span class="pill" style="background: ${c.primary}; color: ${c.background};">${theme.name.split(' ')[0]}</span>
        <span class="pill" style="background: ${c.card_bg}; color: ${c.secondary}; border: 1px solid ${c.card_border};">45 km/h</span>
      </div>
    </div>
    <div class="theme-info">
      <h2>${theme.name}</h2>
      <p>${theme.description}</p>
      <div class="actions">
        <button class="btn btn-preview" data-action="preview" data-key="${key}">Preview</button>
        <button class="btn btn-install" data-action="install" data-key="${key}">Install</button>
      </div>
    </div>
  `;
  return card;
}

function showPreview(key) {
  const theme = themes[key];
  if (!theme) return;
  currentPreview = key;
  const c = theme.colors;
  const preview = document.getElementById('preview');
  const content = document.getElementById('preview-content');
  content.innerHTML = `
    <div class="full-preview" style="
      background: ${c.background};
      color: ${c.text};
      font-family: ${FONT_FAMILY[theme.style] || 'sans-serif'};
    ">
      <div class="header">
        <div>
          <div style="font-size:14px;color:${c.text_dim};">SPEED</div>
          <div class="big-speed" style="color:${c.primary};">45</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:14px;color:${c.text_dim};">${new Date().toLocaleDateString('en-US',{weekday:'long'})}</div>
          <div style="font-size:20px;color:${c.secondary};">${new Date().toLocaleDateString('en-US',{month:'short',day:'numeric'})}</div>
        </div>
      </div>
      <div style="text-align:center;">
        <div class="big-clock" style="color:${c.primary};">${new Date().toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:false})}</div>
        <div style="color:${c.accent};font-size:18px;margin-top:8px;">Now Playing — Sample Track</div>
      </div>
      <div class="grid">
        <div class="app" style="background:${c.card_bg};color:${c.text};border:1px solid ${c.card_border};">📞 Phone</div>
        <div class="app" style="background:${c.card_bg};color:${c.text};border:1px solid ${c.card_border};">🗺️ Maps</div>
        <div class="app" style="background:${c.card_bg};color:${c.text};border:1px solid ${c.card_border};">🎵 Music</div>
        <div class="app" style="background:${c.primary};color:${c.background};">▶ Play</div>
        <div class="app" style="background:${c.card_bg};color:${c.text};border:1px solid ${c.card_border};">⏭ Next</div>
        <div class="app" style="background:${c.card_bg};color:${c.text};border:1px solid ${c.card_border};">🔁 Loop</div>
      </div>
    </div>
  `;
  preview.classList.remove('hidden');
}

function closePreview() {
  document.getElementById('preview').classList.add('hidden');
  currentPreview = null;
}

async function installTheme(key) {
  const theme = themes[key];
  if (!theme) return;

  // Try native installer first (Capacitor plugin)
  if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.ThemeInstaller) {
    try {
      const result = await window.Capacitor.Plugins.ThemeInstaller.install({ themeKey: key });
      if (result.success) {
        showToast(`✓ ${theme.name} installed! Open Car Launcher Pro → Edit Theme → Restore`);
        return;
      }
    } catch (e) {
      console.warn('Native install failed, falling back to download', e);
    }
  }

  // Fallback: download theme files for manual install
  try {
    const themeRes = await fetch(`./themes/${key}/theme.json`);
    const themeBlob = await themeRes.blob();
    downloadBlob(themeBlob, `${key}_theme.json`);
    showToast(`✓ ${theme.name} downloaded! Move to /sdcard/C_Theme/Launcher/${key}/`);
  } catch (e) {
    showToast('Install failed: ' + e.message);
  }
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function showToast(msg) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

// Event listeners
document.addEventListener('click', (e) => {
  const target = e.target;
  if (target.dataset.action === 'preview') {
    showPreview(target.dataset.key);
  } else if (target.dataset.action === 'install') {
    installTheme(target.dataset.key);
  } else if (target.id === 'close-preview') {
    closePreview();
  }
});

document.getElementById('preview').addEventListener('click', (e) => {
  if (e.target.id === 'preview') closePreview();
});

loadThemes();
