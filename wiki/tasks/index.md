---
title: Tasks
hide:
  - navigation
---

# 📋 Tasks

<style>
  body { background: #0a0a0a; color: #e6e6e6; }
  .tasks-gate, .tasks-content { max-width: 800px; margin: 0 auto; padding: 1rem; }
  .tasks-gate {
    text-align: center;
    padding: 3rem 1rem;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    margin-top: 2rem;
  }
  .tasks-gate h2 { margin-bottom: 1rem; color: var(--md-primary-fg-color, #5eead4); }
  .tasks-gate input {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.2);
    color: #e6e6e6;
    padding: 0.6rem 1rem;
    border-radius: 6px;
    font-size: 1rem;
    width: 100%;
    max-width: 280px;
    margin: 0.5rem 0;
    text-align: center;
  }
  .tasks-gate input:focus { outline: 2px solid #5eead4; }
  .tasks-gate button {
    background: #14b8a6;
    color: #0a0a0a;
    border: none;
    padding: 0.6rem 1.5rem;
    border-radius: 6px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    margin-top: 0.5rem;
  }
  .tasks-gate button:hover { background: #0d9488; }
  .tasks-gate .error { color: #f87171; margin-top: 0.5rem; font-size: 0.9rem; min-height: 1.2em; }
  .tasks-gate .hint { color: rgba(255,255,255,0.5); font-size: 0.8rem; margin-top: 0.5rem; }

  .task-list { list-style: none; padding: 0; margin: 0; }
  .task-item {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.6rem;
    display: flex;
    align-items: flex-start;
    gap: 0.8rem;
    transition: opacity 0.2s;
  }
  .task-item.priority-high { border-left: 3px solid #f87171; }
  .task-item.priority-medium { border-left: 3px solid #fbbf24; }
  .task-item.priority-low { border-left: 3px solid #6ee7b7; }
  .task-item.done { opacity: 0.4; }
  .task-item.done .task-title { text-decoration: line-through; }
  .task-check {
    flex-shrink: 0;
    width: 1.4rem;
    height: 1.4rem;
    margin-top: 0.15rem;
    accent-color: #14b8a6;
  }
  .task-content { flex: 1; min-width: 0; }
  .task-title { font-weight: 600; color: #e6e6e6; }
  .task-notes { color: rgba(255,255,255,0.6); font-size: 0.85rem; margin-top: 0.2rem; }
  .task-meta { color: rgba(255,255,255,0.4); font-size: 0.75rem; margin-top: 0.3rem; }
  .task-section-header {
    color: rgba(255,255,255,0.5);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 1.5rem 0 0.5rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid rgba(255,255,255,0.1);
  }
  .empty { color: rgba(255,255,255,0.4); padding: 1rem; text-align: center; }
</style>

<div id="tasks-gate" class="tasks-gate">
  <h2>🔒 Tasks</h2>
  <p>Enter password to view</p>
  <input type="password" id="password-input" placeholder="password" autocomplete="off" />
  <br/>
  <button id="unlock-btn">Unlock</button>
  <div class="error" id="gate-error"></div>
  <div class="hint">Tell Hermes if you need to set or change the password</div>
</div>

<div id="tasks-content" class="tasks-content" style="display:none;">
  <div id="tasks-pending-section" class="task-section">
    <div class="task-section-header" id="pending-header">Pending</div>
    <ul class="task-list" id="pending-list"></ul>
  </div>
  <div id="tasks-done-section" class="task-section">
    <div class="task-section-header" id="done-header">Done</div>
    <ul class="task-list" id="done-list"></ul>
  </div>
  <div class="task-meta" style="text-align:center;margin-top:2rem;" id="last-updated"></div>
</div>

<script>
(function() {
  // SHA-256 of password "oracle". Change this hash to update the password.
  const PASSWORD_HASH = "9202af6ce925b26ae6b25adfff0b2705147e195fa38dd58ae6ecc58ed263751f";

  async function sha256(text) {
    const buf = new TextEncoder().encode(text);
    const hashBuf = await crypto.subtle.digest("SHA-256", buf);
    return Array.from(new Uint8Array(hashBuf)).map(b => b.toString(16).padStart(2, "0")).join("");
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
  }

  function fmtDate(iso) {
    if (!iso) return "";
    try { return new Date(iso).toLocaleString(); } catch (e) { return iso; }
  }
  function fmtDateShort(iso) {
    if (!iso) return "";
    try { return new Date(iso).toLocaleDateString(); } catch (e) { return iso; }
  }

  async function unlock() {
    const pw = document.getElementById("password-input").value;
    const errEl = document.getElementById("gate-error");
    if (!pw) { errEl.textContent = "Enter a password"; return; }
    const hash = await sha256(pw);
    if (hash === PASSWORD_HASH) {
      sessionStorage.setItem("tasks_unlocked", "1");
      document.getElementById("tasks-gate").style.display = "none";
      document.getElementById("tasks-content").style.display = "block";
      errEl.textContent = "";
      loadTasks();
    } else {
      errEl.textContent = "✗ Wrong password";
      document.getElementById("password-input").value = "";
      document.getElementById("password-input").focus();
    }
  }

  async function loadTasks() {
    try {
      const r = await fetch("tasks.json?nocache=" + Date.now());
      if (!r.ok) throw new Error("fetch failed: " + r.status);
      const data = await r.json();
      renderTasks(data);
    } catch (e) {
      document.getElementById("pending-list").innerHTML =
        '<li class="empty">Could not load tasks: ' + escapeHtml(e.message) + '</li>';
    }
  }

  function renderTasks(data) {
    const tasks = (data.tasks || []).slice().sort((a, b) => {
      if (a.status !== b.status) return a.status === "pending" ? -1 : 1;
      const priOrder = { high: 0, medium: 1, low: 2 };
      const ap = priOrder[a.priority] ?? 1;
      const bp = priOrder[b.priority] ?? 1;
      if (ap !== bp) return ap - bp;
      return (a.created || "").localeCompare(b.created || "");
    });

    const pending = tasks.filter(t => t.status === "pending");
    const done = tasks.filter(t => t.status === "done");

    document.getElementById("pending-header").textContent = `Pending (${pending.length})`;
    document.getElementById("done-header").textContent = `Done (${done.length})`;

    document.getElementById("pending-list").innerHTML = pending.length === 0
      ? '<li class="empty">No pending tasks. 🎉</li>'
      : pending.map(taskHtml).join("");

    document.getElementById("done-list").innerHTML = done.length === 0
      ? '' : done.map(taskHtml).join("");

    document.getElementById("done-header").style.display = done.length === 0 ? "none" : "";

    document.getElementById("last-updated").textContent =
      "Last updated " + fmtDate(data.updated);

    document.querySelectorAll(".task-check").forEach(cb => {
      cb.addEventListener("change", (e) => {
        const item = e.target.closest(".task-item");
        if (e.target.checked) {
          item.classList.add("done");
          const meta = item.querySelector(".task-meta");
          meta.innerHTML += " · <em>(tell Hermes to persist)</em>";
        } else {
          item.classList.remove("done");
        }
      });
    });
  }

  function taskHtml(t) {
    const meta = [];
    if (t.priority) meta.push(`priority: ${t.priority}`);
    if (t.due) meta.push(`due: ${fmtDateShort(t.due)}`);
    if (t.created) meta.push(`added: ${fmtDateShort(t.created)}`);
    return `<li class="task-item priority-${t.priority || 'medium'} ${t.status === 'done' ? 'done' : ''}">
      <input type="checkbox" class="task-check" ${t.status === 'done' ? 'checked disabled' : ''} />
      <div class="task-content">
        <div class="task-title">${escapeHtml(t.title || "(untitled)")}</div>
        ${t.notes ? `<div class="task-notes">${escapeHtml(t.notes)}</div>` : ''}
        ${meta.length ? `<div class="task-meta">${meta.join(' · ')}</div>` : ''}
      </div>
    </li>`;
  }

  document.getElementById("unlock-btn").addEventListener("click", unlock);
  document.getElementById("password-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") unlock();
  });

  if (sessionStorage.getItem("tasks_unlocked") === "1") {
    document.getElementById("tasks-gate").style.display = "none";
    document.getElementById("tasks-content").style.display = "block";
    loadTasks();
  } else {
    document.getElementById("password-input").focus();
  }
})();
</script>