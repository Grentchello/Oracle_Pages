---
title: Wallpapers
hide:
  - navigation
---

<style>
  body { background: #0a0a0a; color: #e6e6e6; }
  .container { max-width: 1100px; margin: 0 auto; padding: 1rem; }
  h1 { color: #5eead4; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
  .card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; overflow: hidden; transition: transform 0.2s; }
  .card:hover { transform: scale(1.02); border-color: #5eead4; }
  .card a { color: inherit; text-decoration: none; display: block; }
  .card img { width: 100%; aspect-ratio: 9/19; object-fit: cover; display: block; background: #000; }
  .card .label { padding: 0.5rem 0.8rem; font-size: 0.8rem; color: rgba(255,255,255,0.7); border-top: 1px solid rgba(255,255,255,0.06); word-break: break-all; }
  .filter { margin: 1rem 0; display: flex; gap: 0.5rem; flex-wrap: wrap; }
  .filter button { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.15); color: #e6e6e6; padding: 0.5rem 0.9rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
  .filter button.active { background: #14b8a6; color: #0a0a0a; border-color: #14b8a6; }
  .meta { color: rgba(255,255,255,0.5); font-size: 0.85rem; margin: 0.5rem 0 1.5rem; }
</style>

<div class="container">
  <h1>📱 Wallpapers</h1>
  <p class="meta">From <a href="https://alisonfriend.com/" style="color: #5eead4;">alisonfriend.com</a>. Tap any image to download full resolution. Two sizes per image: iPhone (1170×2532) and Android (1080×1920).</p>

  <div class="filter">
    <button class="active" data-filter="all">All</button>
    <button data-filter="iphone">iPhone</button>
    <button data-filter="android">Android</button>
  </div>

  <div class="grid" id="grid"></div>
</div>

<script>
const files = [
  "030924_0027CR_android_1080x1920.jpg",
  "030924_0027CR_iphone_1170x2532.jpg",
  "030924_0061CR_android_1080x1920.jpg",
  "030924_0061CR_iphone_1170x2532.jpg",
  "030924_0409CR_android_1080x1920.jpg",
  "030924_0409CR_iphone_1170x2532.jpg",
  "030924_0463CR_android_1080x1920.jpg",
  "030924_0463CR_iphone_1170x2532.jpg",
  "030924_0487CR_android_1080x1920.jpg",
  "030924_0487CR_iphone_1170x2532.jpg",
  "360_F_562111583_AcmOoTH53BpjhEJZ1g9BzUejGbj8lMAQ_android_1080x1920.jpg",
  "360_F_562111583_AcmOoTH53BpjhEJZ1g9BzUejGbj8lMAQ_iphone_1170x2532.jpg",
  "AF-Logo-Black_android_1080x1920.jpg",
  "AF-Logo-Black_iphone_1170x2532.jpg",
  "Headshot_in_Studio_B_W_e8d99adb-8d6c-43b9-b720-8acd8468d202_android_1080x1920.jpg",
  "Headshot_in_Studio_B_W_e8d99adb-8d6c-43b9-b720-8acd8468d202_iphone_1170x2532.jpg",
  "OCK_android_1080x1920.jpg",
  "OCK_iphone_1170x2532.jpg",
  "Screenshot_2025-04-22_at_3.36.33_PM_android_1080x1920.jpg",
  "Screenshot_2025-04-22_at_3.36.33_PM_iphone_1170x2532.jpg",
  "Screenshot_2025-10-07_at_3.49.18_PM_android_1080x1920.jpg",
  "Screenshot_2025-10-07_at_3.49.18_PM_iphone_1170x2532.jpg",
  "Screenshot_2025-10-21_at_1.20.10_PM_android_1080x1920.jpg",
  "Screenshot_2025-10-21_at_1.20.10_PM_iphone_1170x2532.jpg",
  "Slide_1_android_1080x1920.jpg",
  "Slide_1_iphone_1170x2532.jpg",
  "Slide_2_android_1080x1920.jpg",
  "Slide_2_iphone_1170x2532.jpg",
  "Slide_3_android_1080x1920.jpg",
  "Slide_3_iphone_1170x2532.jpg",
  "certif_android_1080x1920.jpg",
  "certif_iphone_1170x2532.jpg",
  "dccbe1b5c6f44b50b5ed030d5390db44.thumbnail.0000000000_1100x_android_1080x1920.jpg",
  "dccbe1b5c6f44b50b5ed030d5390db44.thumbnail.0000000000_1100x_iphone_1170x2532.jpg",
  "dccbe1b5c6f44b50b5ed030d5390db44.thumbnail.0000000000_android_1080x1920.jpg",
  "dccbe1b5c6f44b50b5ed030d5390db44.thumbnail.0000000000_iphone_1170x2532.jpg"
];

const base = "/wallpapers/";
const grid = document.getElementById("grid");

function prettyName(f) {
  return f.replace(/^(.*?)_(iphone|android)_.*\.jpg$/, "$1 ($2)");
}

function render(filter) {
  grid.innerHTML = files
    .filter(f => filter === "all" || f.includes("_" + filter + "_"))
    .map(f => `
      <div class="card">
        <a href="${base}${f}" download="${f}">
          <img src="${base}${f}" alt="${prettyName(f)}" loading="lazy" />
          <div class="label">${prettyName(f)}</div>
        </a>
      </div>
    `).join("");
}

document.querySelectorAll(".filter button").forEach(btn => {
  btn.addEventListener("click", (e) => {
    document.querySelectorAll(".filter button").forEach(b => b.classList.remove("active"));
    e.target.classList.add("active");
    render(e.target.dataset.filter);
  });
});

render("all");
</script>