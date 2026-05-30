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

let lastRenderedRunId = null;
let lastRenderedMsgCount = 0;
let lastRenderedTraceLen = -1;
let lastRenderedTraceSignature = "";

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
    item.addEventListener("click", () => {
      selectedId = s.session_id;
      lastRenderedRunId = null;
      lastRenderedMsgCount = 0;
      loadDetail(s.session_id);
      renderSidebar();
    });

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
  const intake = outputs.requirement_intake || {};
  const prioData = outputs.priority_escalation || {};
  const trace = triage.trace || [];
  const trOutput = outputs.triage_router || {};

  const runId = triage.run_id || triage._current_run_id || null;
  const msgCount = session.history.length;
  const traceLen = Array.isArray(trace) ? trace.length : 0;
  const traceSignature = Array.isArray(trace)
    ? trace.map((s) => `${s.agent || ""}:${s.timestamp || ""}:${s.duration_ms || ""}`).join("|")
    : "";

  const isSameTrace =
    runId === lastRenderedRunId &&
    msgCount === lastRenderedMsgCount &&
    traceLen === lastRenderedTraceLen &&
    traceSignature === lastRenderedTraceSignature;
  
  if (!isSameTrace) {
    lastRenderedRunId = runId;
    lastRenderedMsgCount = msgCount;
    lastRenderedTraceLen = traceLen;
    lastRenderedTraceSignature = traceSignature;
  }

  /* Header & WhatsApp Contact */
  document.getElementById("detailName").textContent = session.customer_name;
  document.getElementById("detailMeta").textContent = "Session " + session.session_id + " · " + session.history.length + " pesan";

  const waContactBadge = document.getElementById("waContactBadge");
  const waNumberText = document.getElementById("waNumberText");
  const whatsapp = session.customer_whatsapp;
  if (whatsapp) {
    waContactBadge.style.display = "inline-flex";
    waNumberText.textContent = whatsapp;
    
    // Clean and format number for international wa.me link
    let clean = whatsapp.replace(/\D/g, "");
    if (clean.startsWith("0")) {
      clean = "62" + clean.slice(1);
    }
    waContactBadge.href = "https://wa.me/" + clean;
  } else {
    waContactBadge.style.display = "none";
  }

  /* AI Status badge */
  const missing = normalizeList(intake.missing_information || classifier.missing_information);
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

  /* Support Case Packet (Support Pipeline only) */
  const supportCaseSection = document.getElementById("supportCaseSection");
  const supportCase = final.support_case || null;
  const isRenovation = (trOutput && trOutput.selected_pipeline === "renovation_quote");
  if (supportCase && !isRenovation) {
    supportCaseSection.hidden = false;
    setText("scCategory", supportCase.complaint_category || "-");
    const scPrioEl = document.getElementById("scPriority");
    scPrioEl.textContent = fmt(supportCase.priority) || "-";
    scPrioEl.className = "card-value " + priorityClass(supportCase.priority);
    const scEscEl = document.getElementById("scEscalate");
    if (supportCase.escalation_required) {
      scEscEl.textContent = "⚠️ Ya — Perlu Eskalasi";
      scEscEl.style.color = "var(--danger)";
    } else {
      scEscEl.textContent = "✅ Tidak";
      scEscEl.style.color = "var(--ok)";
    }
    setText("scTeam", fmt(supportCase.escalation_team));
    setText("scSla", supportCase.sla_suggestion || "-");
    setText("scNextAction", supportCase.staff_next_action || "-");
    renderPills(document.getElementById("scDataAvail"), supportCase.data_available || []);
    renderPills(document.getElementById("scDataMissing"), supportCase.data_missing || []);
    setText("scRisk", supportCase.risk_note || "-");
  } else {
    supportCaseSection.hidden = true;
  }

  /* Render Quote if it exists */
  const quoteSection = document.getElementById("quoteSection");
  const quoteCode = final.quote_code || (outputs.quote_builder || {}).quote_code;
  const lineItems = final.line_items || (outputs.quote_builder || {}).line_items || [];
  
  if (quoteCode) {
    quoteSection.hidden = false;
    document.getElementById("qCode").textContent = quoteCode;
    
    const totalVal = final.estimated_total || (outputs.quote_builder || {}).estimated_total || 0;
    document.getElementById("qTotal").textContent = "Rp " + Number(totalVal).toLocaleString("id-ID");
    
    const bStatus = final.budget_status || (outputs.quote_builder || {}).budget_status || "unknown_budget";
    const qBudgetStatus = document.getElementById("qBudgetStatus");
    qBudgetStatus.textContent = fmt(bStatus);
    if (bStatus === "within_budget") {
      qBudgetStatus.style.color = "var(--ok)";
    } else if (bStatus === "over_budget") {
      qBudgetStatus.style.color = "var(--danger)";
    } else {
      qBudgetStatus.style.color = "var(--muted)";
    }
    
    const itemsBody = document.getElementById("qItemsBody");
    itemsBody.innerHTML = "";
    lineItems.forEach((item) => {
      const tr = document.createElement("tr");
      
      const tdSku = document.createElement("td");
      tdSku.textContent = item.sku || "-";
      tdSku.style.fontWeight = "600";
      
      const tdName = document.createElement("td");
      tdName.textContent = item.name || "-";
      
      const tdQty = document.createElement("td");
      tdQty.textContent = Number(item.estimated_qty || item.qty || 0).toLocaleString("id-ID");
      tdQty.style.textAlign = "right";
      tdQty.style.paddingRight = "20px";
      
      const tdUnit = document.createElement("td");
      tdUnit.textContent = item.unit || "-";
      
      const priceVal = item.unit_price || item.price || 0;
      const tdPrice = document.createElement("td");
      tdPrice.textContent = "Rp " + Number(priceVal).toLocaleString("id-ID");
      tdPrice.style.textAlign = "right";
      tdPrice.style.paddingRight = "20px";
      
      const subtotalVal = item.subtotal || (priceVal * (item.estimated_qty || item.qty || 0));
      const tdSub = document.createElement("td");
      tdSub.textContent = "Rp " + Number(subtotalVal).toLocaleString("id-ID");
      tdSub.style.textAlign = "right";
      tdSub.style.paddingRight = "20px";
      tdSub.style.fontWeight = "600";
      tdSub.style.color = "var(--text)";
      
      tr.append(tdSku, tdName, tdQty, tdUnit, tdPrice, tdSub);
      itemsBody.appendChild(tr);
    });
    
    document.getElementById("qNotes").textContent = final.notes || (outputs.quote_builder || {}).notes || "-";
  } else {
    quoteSection.hidden = true;
  }

  /* Render Triage Router if it exists */
  const trSection = document.getElementById("triageRouterSection");
  if (trOutput && Object.keys(trOutput).length > 0) {
    trSection.hidden = false;
    document.getElementById("trPrimaryIntent").textContent = fmt(trOutput.primary_intent);
    document.getElementById("trSelectedPipeline").textContent = fmt(trOutput.selected_pipeline);
    document.getElementById("trPriorityRule").textContent = fmt(trOutput.priority_rule || "standard_routing");
    document.getElementById("trMultiIntent").textContent = trOutput.multi_intent ? "Ya (Multi-Intent)" : "Tidak";
    renderPills(document.getElementById("trSecondaryIntents"), trOutput.secondary_intents);
    document.getElementById("trRoutingReason").textContent = trOutput.routing_reason || "-";
    document.getElementById("trHandoffNotes").textContent = trOutput.staff_handoff_notes || "-";
  } else {
    trSection.hidden = true;
  }

  /* Render Compliance Verifier if it exists */
  const verifierSection = document.getElementById("verifierSection");
  const verifierOutput = outputs.risk_policy_verifier;
  if (verifierOutput) {
    verifierSection.hidden = false;
    
    const riskLevel = verifierOutput.risk_level || "low";
    const vRiskLevel = document.getElementById("vRiskLevel");
    vRiskLevel.textContent = fmt(riskLevel);
    vRiskLevel.className = "card-value " + (riskLevel.toLowerCase() === "high" ? "priority-high" : riskLevel.toLowerCase() === "medium" ? "priority-medium" : "priority-low");
    
    const revRequired = verifierOutput.revision_required;
    const revApplied = verifierOutput.revision_applied;
    const vRevisionStatus = document.getElementById("vRevisionStatus");
    if (revApplied) {
      vRevisionStatus.textContent = "Revisi Berhasil (Audit Lolos)";
      vRevisionStatus.style.color = "var(--ok)";
    } else {
      vRevisionStatus.textContent = revRequired ? "Revisi Diperlukan (Audit Gagal)" : "Lolos Audit (Tanpa Revisi)";
      vRevisionStatus.style.color = revRequired ? "var(--danger)" : "var(--ok)";
    }
    
    document.getElementById("vDebateLog").textContent = verifierOutput.criticism_debate_log || verifierOutput.reasoning || "Tidak ada catatan log kritik.";
  } else {
    verifierSection.hidden = true;
  }

  /* Missing */
  renderPills(document.getElementById("dMissing"), missing);

  /* Steps */
  renderSteps(document.getElementById("dSteps"), normalizeList(final.internal_next_steps));

  /* SLA & Risk */
  setText("dSla", prioData.sla_recommendation);
  setText("dRisk", prioData.business_risk);

  /* Handoff */
  document.getElementById("dHandoff").textContent = buildHandoff(session, final, classifier, prioData, intake, trOutput);

  /* Conversation */
  document.getElementById("dMsgCount").textContent = session.history.length + " msg";
  document.getElementById("dConversation").textContent = session.history.map((m) => (m.role === "customer" ? session.customer_name : "QHome AI") + ": " + m.content).join("\n\n") || "-";

  /* Trace */
  if (!isSameTrace) {
    if (window.simTimeoutId) {
      clearTimeout(window.simTimeoutId);
      window.simTimeoutId = null;
    }
    
    const simBtn = document.getElementById("simBtn");
    const instantBtn = document.getElementById("instantBtn");
    if (trace && trace.length > 0) {
      simBtn.style.display = "inline-flex";
      simBtn.onclick = (e) => {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        playSimulation(trace);
      };
      
      instantBtn.style.display = "inline-flex";
      instantBtn.onclick = (e) => {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        renderStaticTrace(trace);
      };

      // Default to static trace display for staff overview. Live simulation can be triggered manually.
      renderStaticTrace(trace);
    } else {
      simBtn.style.display = "none";
      instantBtn.style.display = "none";
      const traceEl = document.getElementById("dTrace");
      traceEl.innerHTML = '<div style="padding:15px; color:var(--muted); font-size:13px; font-style:italic;">Tidak ada riwayat diskusi agent.</div>';
      document.getElementById("dTraceCount").textContent = "0 agents";
    }
  }

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

function buildHandoff(session, final, classifier, prioData, intake, triageRouter) {
  const missing = normalizeList((intake || {}).missing_information || classifier.missing_information);
  const steps = normalizeList(final.internal_next_steps);
  const tr = triageRouter || {};
  
  const trSection = [];
  if (tr.selected_pipeline) {
    trSection.push(
      "",
      "--- HYBRID TRIAGE ROUTER REPORT ---",
      "Selected Pipeline: " + fmt(tr.selected_pipeline),
      "Primary Intent: " + fmt(tr.primary_intent),
      "Priority Rule: " + fmt(tr.priority_rule || "standard_routing"),
      "Secondary Intents: " + (normalizeList(tr.secondary_intents).join(", ") || "Tidak ada"),
      "Router Reason: " + (tr.routing_reason || "-"),
      "Staff Handoff Notes: " + (tr.staff_handoff_notes || "-")
    );
  }

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
    ...trSection,
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

// Format agent trace outputs with rich artifact summaries
function getRiskClass(val) {
  const v = (val || "").toLowerCase();
  if (v === "high" || v === "tinggi") return "priority-high";
  if (v === "medium" || v === "sedang") return "priority-medium";
  if (v === "low" || v === "rendah") return "priority-low";
  return "";
}

function buildArtifact(fields, notes) {
  const rows = fields.map(f => {
    const cls = f.colored ? getRiskClass(f.value) : "";
    return `<div class="artifact-row">
      <span class="artifact-label">${f.label}</span>
      <span class="artifact-value ${cls}">${f.value || "-"}</span>
    </div>`;
  }).join("");
  const notesHtml = notes
    ? `<div class="artifact-notes">${String(notes).substring(0, 180)}${String(notes).length > 180 ? "…" : ""}</div>`
    : "";
  return `<div class="artifact-card">${rows}${notesHtml}</div>`;
}

function formatTraceBody(step, body) {
  const output = step.output || {};
  const agentName = step.agent || "";
  const safeArr = (v) => (!v ? [] : (Array.isArray(v) ? v : [v]));

  if (agentName.includes("Router") || agentName.includes("Orchestrator") || output.selected_pipeline) {
    body.innerHTML = `
      <div class="trace-triage-summary" style="display:flex; flex-direction:column; gap:10px; font-size:13px; line-height:1.4;">
        <div><strong style="color:var(--ok);">Pipeline:</strong> <span style="font-weight:600; text-transform:uppercase;">${fmt(output.selected_pipeline)}</span></div>
        <div><strong style="color:var(--accent);">Primary Intent:</strong> <span>${fmt(output.primary_intent)}</span></div>
        <div><strong style="color:#ff9800;">Priority Rule:</strong> <span>${fmt(output.priority_rule || "standard_routing")}</span></div>
        <div><strong>Reason:</strong> <span style="color:var(--muted);">${output.routing_reason || "-"}</span></div>
        <div style="background:#fffbeb; border:1px solid #fde68a; padding:8px; border-radius:6px; margin-top:5px; color:#92400e;">
          <strong style="color:#d97706; display:block; margin-bottom:3px;">Staff Handoff Notes:</strong>
          ${output.staff_handoff_notes || "-"}
        </div>
      </div>
    `;
  } else if (agentName.includes("Requirement Intake")) {
    body.innerHTML = buildArtifact([
      { label: "Project Type", value: fmt(output.project_type) },
      { label: "Area", value: output.area_m2 != null ? output.area_m2 + " m²" : "-" },
      { label: "Budget", value: output.budget ? "Rp " + Number(output.budget).toLocaleString("id-ID") : "-" },
      { label: "Kategori", value: safeArr(output.categories_needed).join(", ") || "-" },
      { label: "Info Kurang", value: safeArr(output.missing_information).join(", ") || "Lengkap ✅" },
    ], output.reasoning);
  } else if (agentName.includes("Product Retrieval")) {
    const prods = safeArr(output.recommended_products).map(p => p.name || p.sku).join(", ");
    body.innerHTML = buildArtifact([
      { label: "Produk Ditemukan", value: safeArr(output.recommended_products).length + " item" },
      { label: "Produk", value: prods || "-" },
    ], output.reasoning);
  } else if (agentName.includes("Inventory Snapshot") || agentName.includes("Fallback")) {
    const alerts = safeArr(output.inventory_alerts);
    body.innerHTML = buildArtifact([
      { label: "Status Stok", value: output.stock_status_ok ? "✅ Cukup" : "⚠️ Ada Kendala" },
      { label: "Alert", value: alerts.length ? alerts.join("; ") : "Tidak ada" },
    ], output.reasoning);
  } else if (agentName.includes("Quantity Estimator")) {
    const ests = safeArr(output.estimations).map(e => `${e.name}: ${e.estimated_qty} ${e.unit}`).join(" | ");
    body.innerHTML = buildArtifact([
      { label: "Estimasi Material", value: ests || "-" },
      { label: "Item Dihitung", value: safeArr(output.estimations).length + " item" },
    ], output.reasoning);
  } else if (agentName.includes("Quote Builder")) {
    body.innerHTML = buildArtifact([
      { label: "Quote Code", value: output.quote_code || "-" },
      { label: "Total Estimasi", value: output.estimated_total ? "Rp " + Number(output.estimated_total).toLocaleString("id-ID") : "-" },
      { label: "Budget Status", value: fmt(output.budget_status) || "-" },
      { label: "Jumlah Item", value: safeArr(output.line_items).length + " produk" },
    ], output.reasoning);
  } else if (agentName.includes("Risk") || agentName.includes("Verifier") || agentName.includes("Critic")) {
    body.innerHTML = buildArtifact([
      { label: "Risk Level", value: fmt(output.risk_level) || "-", colored: true },
      { label: "Issues", value: safeArr(output.issues_found).join(", ") || "Tidak ada" },
      { label: "Revisi Diperlukan", value: output.revision_required ? "⚠️ Ya" : "✅ Tidak" },
    ], output.criticism_debate_log || output.reasoning);
  } else if (agentName.includes("Intent") || agentName.includes("Classifier")) {
    body.innerHTML = buildArtifact([
      { label: "Intent", value: fmt(output.intent) || "-" },
      { label: "Category", value: fmt(output.category) || "-" },
      { label: "Confidence", value: output.confidence != null ? (Number(output.confidence) * 100).toFixed(0) + "%" : "-" },
      { label: "Info Kurang", value: safeArr(output.missing_information).join(", ") || "Lengkap ✅" },
    ], output.reasoning);
  } else if (agentName.includes("Knowledge")) {
    body.innerHTML = buildArtifact([
      { label: "Policy Matched", value: safeArr(output.matched_policy_ids).join(", ") || "-" },
      { label: "Confidence", value: output.confidence || "-" },
      { label: "Fakta Relevan", value: safeArr(output.relevant_facts).length + " item" },
    ], output.reasoning);
  } else if (agentName.includes("Solution") || agentName.includes("Planner")) {
    const actions = safeArr(output.recommended_actions).slice(0, 2).join("; ");
    body.innerHTML = buildArtifact([
      { label: "Rencana Aksi", value: actions || "-" },
      { label: "Policy Basis", value: output.policy_basis || "-" },
    ], output.reasoning);
  } else if (agentName.includes("Priority") || agentName.includes("Escalation")) {
    body.innerHTML = buildArtifact([
      { label: "Priority", value: fmt(output.priority) || "-", colored: true },
      { label: "Eskalasi", value: output.escalate ? "⚠️ Ya" : "✅ Tidak" },
      { label: "Tim", value: fmt(output.escalation_team) || "-" },
      { label: "SLA", value: output.sla_recommendation || "-" },
    ], output.business_risk || output.reasoning);
  } else if (agentName.includes("QA") || agentName.includes("Final") || agentName.includes("Handoff") || agentName.includes("Response")) {
    const replyPreview = (output.customer_reply || output.reply || "").substring(0, 120);
    body.innerHTML = buildArtifact([
      { label: "Reply Preview", value: replyPreview + (replyPreview.length >= 120 ? "…" : "") },
      { label: "Eskalasi", value: (output.escalate || output.contact_required) ? "⚠️ Ya" : "✅ Tidak" },
      { label: "Steps", value: safeArr(output.internal_next_steps).length + " tindakan" },
    ], output.reasoning);
  } else {
    body.textContent = output.reasoning || JSON.stringify(output, null, 2);
  }
}

// Global simulation timer
window.simTimeoutId = null;

function renderStaticTrace(trace) {
  if (window.simTimeoutId) {
    clearTimeout(window.simTimeoutId);
    window.simTimeoutId = null;
  }
  document.getElementById("dTraceCount").textContent = trace.length + " agents (Selesai)";
  const traceEl = document.getElementById("dTrace");
  traceEl.innerHTML = "";
  trace.forEach((step) => {
    const item = document.createElement("div");
    item.className = "trace-item";
    const header = document.createElement("div");
    header.className = "trace-agent-name";
    const durText = step.duration_ms != null ? `<span class="trace-duration">${(step.duration_ms / 1000).toFixed(1)}s</span>` : "";
    const typeText = step.agent_type ? `<span class="agent-type-label">${step.agent_type}</span>` : "";
    header.innerHTML = `<span class="agent-dot" style="background:#25d366;"></span><div class="trace-agent-info"><strong>${fmt(step.agent)}</strong>${typeText}</div>${durText}`;
    const body = document.createElement("div");
    body.className = "trace-body";
    formatTraceBody(step, body);
    item.append(header, body);
    traceEl.append(item);
  });
  traceEl.scrollTop = traceEl.scrollHeight;
}

function playSimulation(trace) {
  if (window.simTimeoutId) clearTimeout(window.simTimeoutId);
  const traceEl = document.getElementById("dTrace");
  traceEl.innerHTML = "";
  
  let index = 0;
  
  function nextStep() {
    // Remove previous typing indicator if it exists
    const oldIndicator = document.getElementById("simTypingIndicator");
    if (oldIndicator) oldIndicator.remove();
    
    if (index >= trace.length) {
      document.getElementById("dTraceCount").textContent = trace.length + " agents (Simulasi Selesai)";
      window.simTimeoutId = null;
      return;
    }
    
    const step = trace[index];
    document.getElementById("dTraceCount").textContent = `Simulasi: Langkah ${index + 1} dari ${trace.length}...`;

    // Add real step card
    const item = document.createElement("div");
    item.className = "trace-item";
    const header = document.createElement("div");
    header.className = "trace-agent-name";
    const durText = step.duration_ms != null ? `<span class="trace-duration">${(step.duration_ms / 1000).toFixed(1)}s</span>` : "";
    const typeText = step.agent_type ? `<span class="agent-type-label">${step.agent_type}</span>` : "";
    header.innerHTML = `<span class="agent-dot" style="background:#25d366;"></span><div class="trace-agent-info"><strong>${fmt(step.agent)}</strong>${typeText}</div>${durText}`;
    const body = document.createElement("div");
    body.className = "trace-body";
    formatTraceBody(step, body);
    item.append(header, body);
    traceEl.append(item);
    
    index++;
    
    // If there is a next step, append premium typing indicator
    if (index < trace.length) {
      const nextStepObj = trace[index];
      const indicator = document.createElement("div");
      indicator.id = "simTypingIndicator";
      indicator.className = "trace-item";
      indicator.style.borderStyle = "dashed";
      indicator.style.opacity = "0.7";
      indicator.innerHTML = `
        <div class="trace-agent-name" style="background:transparent; border:none; display:flex; align-items:center; gap:8px;">
          <div class="typing-dots" style="transform: scale(0.6); margin:0; display:flex; gap:3px;">
            <span style="background:var(--brand);"></span>
            <span style="background:var(--brand);"></span>
            <span style="background:var(--brand);"></span>
          </div>
          <span style="font-style:italic; font-weight:normal; font-size:11px;">Mempersiapkan ${fmt(nextStepObj.agent)}...</span>
        </div>
      `;
      traceEl.append(indicator);
    }
    
    traceEl.scrollTop = traceEl.scrollHeight;
    window.simTimeoutId = setTimeout(nextStep, 1500);
  }
  
  nextStep();
}
