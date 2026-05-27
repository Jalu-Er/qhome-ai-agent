/* QHome Staff Dashboard */

const ticketList = document.getElementById("ticketList");
const ticketCount = document.getElementById("ticketCount");
const detailEmpty = document.getElementById("detailEmpty");
const detailContent = document.getElementById("detailContent");
const copyBtn = document.getElementById("copyBtn");
const saveNotesBtn = document.getElementById("saveNotesBtn");
const staffNotesEl = document.getElementById("staffNotes");

let sessions = [];
let selectedId = null;
let activeFilter = "all";

/* Filter buttons */
document.querySelectorAll(".filter-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    activeFilter = btn.dataset.filter;
    renderSidebar();
  });
});

/* Workflow status buttons */
document.querySelectorAll(".wf-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (!selectedId) return;
    updateSession(selectedId, { staff_status: btn.dataset.status });
  });
});

/* Save notes */
saveNotesBtn.addEventListener("click", () => {
  if (!selectedId) return;
  updateSession(selectedId, { staff_notes: staffNotesEl.value });
});

/* Copy handoff */
copyBtn.addEventListener("click", async () => {
  const text = document.getElementById("dHandoff").textContent;
  if (!text || text === "-") return;
  try { await navigator.clipboard.writeText(text); copyBtn.textContent = "Copied!"; }
  catch { copyBtn.textContent = "Selected"; }
  setTimeout(() => { copyBtn.textContent = "Copy"; }, 1500);
});

/* Poll sessions every 3s */
loadSessions();
setInterval(loadSessions, 3000);

async function loadSessions() {
  try {
    const res = await fetch("/api/sessions");
    sessions = await res.json();
    ticketCount.textContent = sessions.length + " ticket" + (sessions.length !== 1 ? "s" : "");
    renderSidebar();
    /* Only refresh detail if staff is not actively editing notes */
    if (selectedId && document.activeElement !== staffNotesEl) {
      const still = sessions.find((s) => s.session_id === selectedId);
      if (still) loadDetail(selectedId);
    }
  } catch { /* silent */ }
}

async function updateSession(sid, data) {
  try {
    await fetch("/api/session/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sid, ...data }),
    });
    await loadSessions();
    if (data.staff_notes !== undefined) {
      saveNotesBtn.textContent = "Tersimpan!";
      setTimeout(() => { saveNotesBtn.textContent = "Simpan"; }, 1200);
    }
  } catch { /* silent */ }
}

function renderSidebar() {
  ticketList.innerHTML = "";
  const filtered = filterSessions(sessions);
  if (!filtered.length) {
    ticketList.innerHTML = '<div class="sidebar-empty">Belum ada ticket.</div>';
    return;
  }
  filtered.forEach((s) => {
    const item = document.createElement("div");
    item.className = "ticket-item" + (s.session_id === selectedId ? " active" : "");
    item.addEventListener("click", () => { selectedId = s.session_id; loadDetail(s.session_id); renderSidebar(); });

    const top = document.createElement("div");
    top.className = "ticket-item-top";
    const name = document.createElement("span");
    name.className = "ticket-name";
    name.textContent = s.customer_name;
    const badge = document.createElement("span");
    badge.className = "priority-dot " + priorityClass(s.priority);
    badge.textContent = fmt(s.priority);
    top.append(name, badge);

    const preview = document.createElement("p");
    preview.className = "ticket-preview";
    preview.textContent = s.last_message || "-";

    const meta = document.createElement("div");
    meta.className = "ticket-item-meta";
    const wfBadge = document.createElement("span");
    wfBadge.className = "ticket-status-dot " + staffStatusDot(s.staff_status);
    wfBadge.textContent = staffLabel(s.staff_status);
    const time = document.createElement("span");
    time.className = "ticket-time";
    time.textContent = formatTime(s.updated_at);
    meta.append(wfBadge, time);

    item.append(top, preview, meta);
    ticketList.append(item);
  });
}

function filterSessions(list) {
  if (activeFilter === "all") return list;
  if (activeFilter === "new") return list.filter((s) => s.staff_status === "new");
  if (activeFilter === "in_progress") return list.filter((s) => s.staff_status === "in_progress");
  if (activeFilter === "done") return list.filter((s) => s.staff_status === "done");
  if (activeFilter === "needs_staff") return list.filter((s) => s.ai_status === "needs_staff");
  if (activeFilter === "waiting_info") return list.filter((s) => s.ai_status === "waiting_info");
  return list;
}

async function loadDetail(sid) {
  try {
    const res = await fetch("/api/session?id=" + encodeURIComponent(sid));
    const data = await res.json();
    renderDetail(data);
  } catch { /* silent */ }
}

function renderDetail(session) {
  detailEmpty.hidden = true;
  detailContent.hidden = false;

  const triage = session.triage || {};
  const final = triage.final || {};
  const outputs = triage.agent_outputs || {};
  const classifier = outputs.intent_classifier || {};
  const prioData = outputs.priority_escalation || {};
  const trace = triage.trace || [];

  /* Header */
  document.getElementById("detailName").textContent = session.customer_name;
  document.getElementById("detailMeta").textContent = "Session " + session.session_id + " · " + session.history.length + " pesan";

  /* AI Status badge */
  const missing = normalizeList(classifier.missing_information);
  let aiStatus, aiStatusClass;
  if (missing.length) { aiStatus = "Menunggu Info"; aiStatusClass = "warn"; }
  else if (final.escalate) { aiStatus = "Perlu Staff"; aiStatusClass = "danger"; }
  else { aiStatus = "Resolved"; aiStatusClass = "ok"; }
  const sb = document.getElementById("detailAiStatus");
  sb.textContent = "AI: " + aiStatus;
  sb.className = "status-badge " + aiStatusClass;

  /* Staff workflow buttons */
  const currentWf = session.staff_status || "new";
  document.querySelectorAll(".wf-btn").forEach((btn) => {
    btn.classList.toggle("wf-active", btn.dataset.status === currentWf);
  });

  /* Staff notes */
  staffNotesEl.value = session.staff_notes || "";

  /* Cards */
  setText("dIntent", fmt(final.intent));
  setText("dCategory", fmt(final.category));
  const pe = document.getElementById("dPriority");
  pe.textContent = fmt(final.priority);
  pe.className = "card-value " + priorityClass(final.priority);

  const esc = document.getElementById("dEscalate");
  if (final.escalate === true) { esc.textContent = "Ya — Eskalasi"; esc.className = "card-value badge-escalate-true"; }
  else if (final.escalate === false) { esc.textContent = "Tidak"; esc.className = "card-value badge-escalate-false"; }
  else { esc.textContent = "-"; esc.className = "card-value"; }

  setText("dTeam", fmt(final.escalation_team));
  const ts = document.getElementById("dTicketStatus");
  ts.textContent = aiStatus;
  ts.className = "card-value " + (aiStatusClass === "danger" ? "badge-high" : aiStatusClass === "warn" ? "badge-medium" : "badge-low");

  /* Customer Reply */
  document.getElementById("dCustomerReply").textContent = final.customer_reply || "-";

  /* Missing */
  renderPills(document.getElementById("dMissing"), missing);

  /* Steps */
  renderSteps(document.getElementById("dSteps"), normalizeList(final.internal_next_steps));

  /* SLA & Risk */
  setText("dSla", prioData.sla_recommendation);
  setText("dRisk", prioData.business_risk);

  /* Handoff */
  document.getElementById("dHandoff").textContent = buildHandoff(session, final, classifier, prioData);

  /* Conversation */
  document.getElementById("dMsgCount").textContent = session.history.length + " msg";
  document.getElementById("dConversation").textContent = session.history.map((m) => (m.role === "customer" ? session.customer_name : "QHome AI") + ": " + m.content).join("\n\n") || "-";

  /* Trace */
  document.getElementById("dTraceCount").textContent = trace.length + " agent" + (trace.length !== 1 ? "s" : "");
  const traceEl = document.getElementById("dTrace");
  traceEl.innerHTML = "";
  trace.forEach((step) => {
    const item = document.createElement("div");
    item.className = "trace-item";
    const header = document.createElement("div");
    header.className = "trace-agent-name";
    header.innerHTML = '<span class="agent-dot"></span>' + fmt(step.agent);
    const body = document.createElement("div");
    body.className = "trace-body";
    body.textContent = (step.output || {}).reasoning || JSON.stringify(step.output, null, 2);
    item.append(header, body);
    traceEl.append(item);
  });

  /* Run ID */
  setText("dRunId", triage.run_id);
}

/* Helpers */
function setText(id, val) { document.getElementById(id).textContent = val || "-"; }

function fmt(val) {
  if (!val) return "-";
  return String(val).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function priorityClass(p) {
  const v = (p || "").toLowerCase();
  if (v === "high" || v === "critical") return "priority-high";
  if (v === "medium") return "priority-medium";
  if (v === "low") return "priority-low";
  return "priority-none";
}

function staffStatusDot(s) {
  if (s === "in_progress") return "dot-warn";
  if (s === "done") return "dot-ok";
  return "dot-new";
}

function staffLabel(s) {
  if (s === "in_progress") return "Proses";
  if (s === "done") return "Selesai";
  return "Baru";
}

function formatTime(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
  } catch { return ""; }
}

function renderPills(el, items) {
  el.innerHTML = "";
  const arr = normalizeList(items);
  if (!arr.length) { el.innerHTML = '<li class="pill-empty">Tidak ada</li>'; return; }
  arr.forEach((t) => { const li = document.createElement("li"); li.textContent = t; el.append(li); });
}

function renderSteps(el, items) {
  el.innerHTML = "";
  const arr = normalizeList(items);
  if (!arr.length || (arr.length === 1 && !arr[0])) { el.innerHTML = '<li class="step-empty">Tidak ada</li>'; return; }
  arr.forEach((t) => { const li = document.createElement("li"); li.textContent = typeof t === "string" ? t : JSON.stringify(t); el.append(li); });
}

function buildHandoff(session, final, classifier, prioData) {
  const missing = normalizeList(classifier.missing_information);
  const steps = normalizeList(final.internal_next_steps);
  return [
    "Customer: " + session.customer_name,
    "Session: " + session.session_id,
    "Staff Status: " + staffLabel(session.staff_status || "new"),
    "Intent: " + fmt(final.intent),
    "Category: " + fmt(final.category),
    "Priority: " + fmt(final.priority),
    "Escalate: " + (final.escalate ? "Ya" : "Tidak"),
    "Team: " + fmt(final.escalation_team),
    "", "SLA: " + (prioData.sla_recommendation || "-"),
    "Risk: " + (prioData.business_risk || "-"),
    "", "Missing:",
    ...(missing.length ? missing.map((i) => "- " + i) : ["- Tidak ada"]),
    "", "Next Steps:",
    ...(steps.length ? steps.map((i) => "- " + i) : ["- Tidak ada"]),
    "", "Notes: " + (session.staff_notes || "-"),
  ].join("\n");
}

function normalizeList(value) {
  if (Array.isArray(value)) {
    return value.filter((item) => item !== null && item !== undefined && item !== "").map(formatListItem);
  }
  if (value === null || value === undefined || value === "") return [];
  if (typeof value === "object") {
    return Object.entries(value).map(([key, item]) => key + ": " + formatListItem(item));
  }
  return [String(value)];
}

function formatListItem(value) {
  if (typeof value === "string") return value;
  if (value === null || value === undefined) return "";
  return JSON.stringify(value);
}
