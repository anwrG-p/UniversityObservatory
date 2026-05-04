/**
 * dashboard.js – University Observatory MAS Dashboard
 * All API calls, Chart.js charts, table pagination, and UI interactions.
 */

"use strict";

// ── Constants ────────────────────────────────────────────
const API   = "";          // same origin
const COLORS = [
  "#63b3ed","#b794f4","#68d391","#f6ad55","#fc8181",
  "#4fd1c5","#f687b3","#a3e635","#fbbf24","#38bdf8"
];
const TYPE_COLORS = {
  internship:       "#63b3ed",
  scholarship:      "#b794f4",
  fellowship:       "#f6ad55",
  course:           "#68d391",
  research_project: "#4fd1c5",
  postdoc:          "#fc8181",
};
const TYPE_BADGE = {
  internship:       "badge-blue",
  scholarship:      "badge-purple",
  fellowship:       "badge-orange",
  course:           "badge-green",
  research_project: "badge-teal",
  postdoc:          "badge-pink",
};

// ── State ─────────────────────────────────────────────────
let allOpportunities = [];
let allClusters      = [];
let allUsers         = [];
let currentPage      = 0;
const PAGE_SIZE      = 15;
let activeUserId     = null;
let chartDistrib     = null;
let chartClusters    = null;

// ── Helpers ───────────────────────────────────────────────
const $  = id => document.getElementById(id);
const el = (tag, cls, html) => {
  const e = document.createElement(tag);
  if (cls)  e.className   = cls;
  if (html) e.innerHTML   = html;
  return e;
};

async function apiFetch(path) {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${path}`);
  return res.json();
}

function showToast(msg, duration = 3000) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), duration);
}

function typeBadge(type) {
  const cls = TYPE_BADGE[type] || "badge-blue";
  return `<span class="badge ${cls}">${type.replace(/_/g, " ")}</span>`;
}

function daysUntil(dateStr) {
  if (!dateStr) return null;
  const diff = Math.ceil((new Date(dateStr) - new Date()) / 86400000);
  return diff;
}

// ── Load Stats ────────────────────────────────────────────
async function loadStats() {
  try {
    const s = await apiFetch("/api/stats");
    $("stat-opps").textContent     = s.opportunities;
    $("stat-users").textContent    = s.users;
    $("stat-clusters").textContent = s.clusters;
    $("stat-recs").textContent     = s.recommendations;
    $("stat-notifs").textContent   = s.unread_notifications;
    renderDistribChart(s.by_type || {});
  } catch (e) { console.error("Stats:", e); }
}

// ── Distribution Chart ────────────────────────────────────
function renderDistribChart(byType) {
  const labels = Object.keys(byType).map(k => k.replace(/_/g," "));
  const data   = Object.values(byType);
  const colors = labels.map((_, i) => COLORS[i % COLORS.length]);

  if (chartDistrib) chartDistrib.destroy();
  chartDistrib = new Chart($("chart-distribution"), {
    type: "doughnut",
    data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0, hoverOffset: 8 }] },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: "#94a3b8", font: { size: 11 }, padding: 12, boxWidth: 12 }
        },
        tooltip: {
          backgroundColor: "#0d1628",
          titleColor: "#e2e8f0",
          bodyColor: "#94a3b8",
          borderColor: "rgba(255,255,255,0.08)",
          borderWidth: 1,
        }
      },
      cutout: "65%",
    }
  });
}

// ── Cluster Bar Chart ─────────────────────────────────────
function renderClusterChart(clusters) {
  const labels = clusters.map(c => c.name || `Cluster ${c.id}`);
  const counts = clusters.map(c => c.opp_count || 0);
  const colors = labels.map((_, i) => COLORS[i % COLORS.length]);

  if (chartClusters) chartClusters.destroy();
  chartClusters = new Chart($("chart-clusters"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Opportunities",
        data: counts,
        backgroundColor: colors.map(c => c + "aa"),
        borderColor: colors,
        borderWidth: 1,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true, indexAxis: "y",
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0d1628", titleColor: "#e2e8f0", bodyColor: "#94a3b8",
          borderColor: "rgba(255,255,255,0.08)", borderWidth: 1,
        }
      },
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#94a3b8" } },
        y: { grid: { display: false }, ticks: { color: "#94a3b8", font: { size: 11 } } }
      }
    }
  });
}

// ── Load Opportunities ────────────────────────────────────
async function loadOpportunities(type = "", location = "") {
  let url = "/api/opportunities?limit=300";
  if (type)     url += `&type=${encodeURIComponent(type)}`;
  if (location) url += `&location=${encodeURIComponent(location)}`;
  try {
    const data = await apiFetch(url);
    allOpportunities = data.opportunities || [];
    currentPage = 0;
    renderTable();
    $("opp-count-badge").textContent = allOpportunities.length;
  } catch (e) {
    $("opp-tbody").innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">⚠️</div>Failed to load opportunities.</div></td></tr>`;
  }
}

// ── Render Table ──────────────────────────────────────────
function renderTable() {
  const tbody  = $("opp-tbody");
  const start  = currentPage * PAGE_SIZE;
  const slice  = allOpportunities.slice(start, start + PAGE_SIZE);

  if (!slice.length) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">🔍</div>No opportunities found.</div></td></tr>`;
    $("opp-showing").textContent = "No results";
    return;
  }

  tbody.innerHTML = slice.map((o, i) => {
    const days = daysUntil(o.deadline);
    const urgency = days !== null && days < 30 ? ' style="color:#fc8181"' : '';
    const clusterName = (allClusters.find(c => c.id === o.cluster_id) || {}).name || "—";
    return `<tr>
      <td class="td-title" style="color:#475569">${start + i + 1}</td>
      <td class="td-title" title="${o.title}">${o.title.length > 50 ? o.title.slice(0, 50) + "…" : o.title}</td>
      <td>${typeBadge(o.type)}</td>
      <td class="td-desc" title="${o.location || ''}">${o.location || "—"}</td>
      <td class="td-deadline"${urgency}>${o.deadline || "—"}${days !== null && days < 30 ? ' 🔥' : ''}</td>
      <td style="font-size:0.75rem;color:#94a3b8">${clusterName}</td>
      <td><a class="link-btn" href="${o.url || '#'}" target="_blank" rel="noopener">View ↗</a></td>
    </tr>`;
  }).join("");

  const total = allOpportunities.length;
  const end   = Math.min(start + PAGE_SIZE, total);
  $("opp-showing").textContent = `Showing ${start + 1}–${end} of ${total}`;
  $("btn-prev").disabled = currentPage === 0;
  $("btn-next").disabled = end >= total;
}

// ── Load Clusters ─────────────────────────────────────────
async function loadClusters() {
  try {
    const data = await apiFetch("/api/clusters");
    allClusters = data.clusters || [];

    // Count opps per cluster
    allClusters.forEach(c => {
      c.opp_count = allOpportunities.filter(o => o.cluster_id === c.id).length;
    });

    renderClusterChart(allClusters);
    renderClusterList();
  } catch (e) { console.error("Clusters:", e); }
}

function renderClusterList() {
  const list = $("cluster-list");
  list.innerHTML = allClusters.map((c, i) => `
    <div class="cluster-item" data-cid="${c.id}">
      <div class="cluster-dot" style="background:${COLORS[i % COLORS.length]}"></div>
      <span class="cluster-name">${c.name || `Cluster ${c.id}`}</span>
      <span class="cluster-count">${c.opp_count || 0}</span>
    </div>
  `).join("");

  list.querySelectorAll(".cluster-item").forEach(item => {
    item.addEventListener("click", () => {
      list.querySelectorAll(".cluster-item").forEach(i => i.classList.remove("active"));
      item.classList.add("active");
      showClusterDetail(parseInt(item.dataset.cid));
    });
  });
}

function showClusterDetail(clusterId) {
  const cluster = allClusters.find(c => c.id === clusterId);
  const opps    = allOpportunities.filter(o => o.cluster_id === clusterId);
  const detail  = $("cluster-detail");

  if (!cluster || !opps.length) {
    detail.innerHTML = `<div class="empty-state"><div class="empty-icon">📭</div>No opportunities in this cluster.</div>`;
    return;
  }

  detail.innerHTML = `
    <p class="section-title">${cluster.name}</p>
    <p style="font-size:0.78rem;color:#94a3b8;margin-bottom:1rem">
      Keywords: <span style="color:#63b3ed">${cluster.keywords || "—"}</span>
    </p>
    <div style="display:flex;flex-direction:column;gap:8px;max-height:300px;overflow-y:auto">
      ${opps.slice(0,20).map(o => `
        <div style="display:flex;align-items:center;gap:10px;padding:8px 10px;background:rgba(255,255,255,0.02);border-radius:6px;border:1px solid rgba(255,255,255,0.06)">
          ${typeBadge(o.type)}
          <span style="flex:1;font-size:0.83rem;font-weight:600;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${o.title}">${o.title}</span>
          <a class="link-btn" href="${o.url || '#'}" target="_blank" rel="noopener">↗</a>
        </div>
      `).join("")}
    </div>
  `;
}

// ── Load Users ────────────────────────────────────────────
async function loadUsers() {
  try {
    const data = await apiFetch("/api/users");
    allUsers = data.users || [];
    renderUserTabs();
    renderNotifUserSelect();
  } catch (e) { console.error("Users:", e); }
}

function renderUserTabs() {
  const tabs = $("user-tabs");
  const existing = tabs.querySelector(".filter-label");
  tabs.innerHTML = "";
  if (existing) tabs.appendChild(existing);

  allUsers.forEach(u => {
    const btn = el("button", "user-tab", `👤 ${u.name.split(" ")[0]}`);
    btn.title = u.name;
    btn.dataset.uid = u.id;
    btn.addEventListener("click", () => {
      tabs.querySelectorAll(".user-tab").forEach(t => t.classList.remove("active"));
      btn.classList.add("active");
      loadRecommendations(u.id);
    });
    tabs.appendChild(btn);
  });
}

function renderNotifUserSelect() {
  const sel = $("notif-user-select");
  sel.innerHTML = '<option value="">Select user</option>';
  allUsers.forEach(u => {
    sel.innerHTML += `<option value="${u.id}">${u.name}</option>`;
  });
  sel.addEventListener("change", () => {
    if (sel.value) loadNotifications(parseInt(sel.value));
  });
}

// ── Load Recommendations ──────────────────────────────────
async function loadRecommendations(userId) {
  const list = $("rec-list");
  list.innerHTML = `<div class="empty-state"><div class="spinner"></div>&nbsp; Loading…</div>`;
  try {
    const data = await apiFetch(`/api/recommendations/${userId}`);
    const recs  = data.recommendations || [];
    if (!recs.length) {
      list.innerHTML = `<div class="empty-state"><div class="empty-icon">🎯</div>No recommendations yet. Run the pipeline first.</div>`;
      return;
    }
    list.innerHTML = recs.slice(0, 10).map((r, i) => `
      <div class="rec-card">
        <div class="rec-rank">#${i + 1}</div>
        <div class="rec-info">
          <div class="rec-title">${r.title}</div>
          <div class="rec-meta">
            ${typeBadge(r.type)}
            <span>📍 ${r.location || "—"}</span>
            <span>⏰ ${r.deadline || "—"}</span>
          </div>
        </div>
        <div class="rec-score">${(r.score * 100).toFixed(1)}%</div>
      </div>
    `).join("");
  } catch (e) {
    list.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div>Failed to load recommendations.</div>`;
  }
}

// ── Load Notifications ────────────────────────────────────
async function loadNotifications(userId) {
  const list = $("notif-list");
  list.innerHTML = `<div class="empty-state"><div class="spinner"></div>&nbsp; Loading…</div>`;
  try {
    const data  = await apiFetch(`/api/notifications/${userId}`);
    const notifs = data.notifications || [];
    if (!notifs.length) {
      list.innerHTML = `<div class="empty-state"><div class="empty-icon">✅</div>No notifications.</div>`;
      return;
    }
    list.innerHTML = notifs.slice(0, 8).map(n => `
      <div class="notif-item ${n.status === 'unread' ? 'unread' : ''}">
        <div class="notif-dot ${n.status !== 'unread' ? 'read' : ''}"></div>
        <div class="notif-msg">${n.message || n.opp_title}</div>
        <div class="notif-time">${n.created_at ? n.created_at.slice(0, 10) : "—"}</div>
      </div>
    `).join("");
  } catch (e) {
    list.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div>Failed to load notifications.</div>`;
  }
}

// ── Pipeline ──────────────────────────────────────────────
async function runPipeline() {
  const btn    = $("btn-run-pipeline");
  const status = $("pipeline-status");

  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span> Running…`;
  status.textContent = "⚙️ Pipeline running — scraping → classifying → clustering → recommending…";
  status.className   = "running";
  status.style.display = "block";

  try {
    const result = await fetch(`${API}/api/run-pipeline`, { method: "POST" });
    const data   = await result.json();

    if (data.status === "ok") {
      status.textContent = "✅ Pipeline completed successfully!";
      status.className   = "";
      showToast("✅ Pipeline complete! Dashboard refreshed.");
      await refreshAll();
    } else {
      throw new Error(data.error || "Unknown error");
    }
  } catch (e) {
    status.textContent = `❌ Pipeline error: ${e.message}`;
    status.className   = "error";
    showToast("❌ Pipeline failed. Check console.");
  } finally {
    btn.disabled = false;
    btn.innerHTML = "⚡ Run Pipeline";
    setTimeout(() => { status.style.display = "none"; }, 8000);
  }
}

// ── Refresh all ────────────────────────────────────────────
async function refreshAll() {
  await loadStats();
  await loadOpportunities();
  await loadClusters();
  await loadUsers();
}

// ── Init ──────────────────────────────────────────────────
async function init() {
  // Event listeners
  $("btn-run-pipeline").addEventListener("click", runPipeline);
  $("btn-filter").addEventListener("click", () => {
    loadOpportunities($("filter-type").value, $("filter-location").value);
  });
  $("btn-reset-filter").addEventListener("click", () => {
    $("filter-type").value = "";
    $("filter-location").value = "";
    loadOpportunities();
  });
  $("btn-prev").addEventListener("click", () => { currentPage--; renderTable(); });
  $("btn-next").addEventListener("click", () => { currentPage++; renderTable(); });

  // Load initial data
  await loadStats();
  await loadOpportunities();
  await loadClusters();
  await loadUsers();
}

document.addEventListener("DOMContentLoaded", init);
