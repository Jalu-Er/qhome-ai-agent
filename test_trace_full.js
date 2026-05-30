const fs = require('fs');
const traces = fs.readFileSync('/home/jalue/lomba/qhome-ai-agent/runs-test/bulk-order-test-run/interactions.jsonl', 'utf-8').trim().split('\n').map(JSON.parse);

function fmt(val) {
  if (!val) return "-";
  return String(val).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

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
      { label: "Kategori", value: (output.categories_needed || []).join(", ") || "-" },
      { label: "Info Kurang", value: (output.missing_information || []).join(", ") || "Lengkap ✅" },
    ], output.reasoning);
  } else if (agentName.includes("Product Retrieval")) {
    const prods = (output.recommended_products || []).map(p => p.name || p.sku).join(", ");
    body.innerHTML = buildArtifact([
      { label: "Produk Ditemukan", value: (output.recommended_products || []).length + " item" },
      { label: "Produk", value: prods || "-" },
    ], output.reasoning);
  } else if (agentName.includes("Inventory Snapshot") || agentName.includes("Fallback")) {
    const alerts = output.inventory_alerts || [];
    body.innerHTML = buildArtifact([
      { label: "Status Stok", value: output.stock_status_ok ? "✅ Cukup" : "⚠️ Ada Kendala" },
      { label: "Alert", value: alerts.length ? alerts.join("; ") : "Tidak ada" },
    ], output.reasoning);
  } else if (agentName.includes("Quantity Estimator")) {
    const ests = (output.estimations || []).map(e => `${e.name}: ${e.estimated_qty} ${e.unit}`).join(" | ");
    body.innerHTML = buildArtifact([
      { label: "Estimasi Material", value: ests || "-" },
      { label: "Item Dihitung", value: (output.estimations || []).length + " item" },
    ], output.reasoning);
  } else if (agentName.includes("Quote Builder")) {
    body.innerHTML = buildArtifact([
      { label: "Quote Code", value: output.quote_code || "-" },
      { label: "Total Estimasi", value: output.estimated_total ? "Rp " + Number(output.estimated_total).toLocaleString("id-ID") : "-" },
      { label: "Budget Status", value: fmt(output.budget_status) || "-" },
      { label: "Jumlah Item", value: (output.line_items || []).length + " produk" },
    ], output.reasoning);
  } else if (agentName.includes("Risk") || agentName.includes("Verifier") || agentName.includes("Critic")) {
    body.innerHTML = buildArtifact([
      { label: "Risk Level", value: fmt(output.risk_level) || "-", colored: true },
      { label: "Issues", value: (output.issues_found || []).join(", ") || "Tidak ada" },
      { label: "Revisi Diperlukan", value: output.revision_required ? "⚠️ Ya" : "✅ Tidak" },
    ], output.criticism_debate_log || output.reasoning);
  } else if (agentName.includes("Intent") || agentName.includes("Classifier")) {
    body.innerHTML = buildArtifact([
      { label: "Intent", value: fmt(output.intent) || "-" },
      { label: "Category", value: fmt(output.category) || "-" },
      { label: "Confidence", value: output.confidence != null ? (Number(output.confidence) * 100).toFixed(0) + "%" : "-" },
      { label: "Info Kurang", value: (output.missing_information || []).join(", ") || "Lengkap ✅" },
    ], output.reasoning);
  } else if (agentName.includes("Knowledge")) {
    body.innerHTML = buildArtifact([
      { label: "Policy Matched", value: (output.matched_policy_ids || []).join(", ") || "-" },
      { label: "Confidence", value: output.confidence || "-" },
      { label: "Fakta Relevan", value: (output.relevant_facts || []).length + " item" },
    ], output.reasoning);
  } else if (agentName.includes("Solution") || agentName.includes("Planner")) {
    const actions = (output.recommended_actions || []).slice(0, 2).join("; ");
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
      { label: "Steps", value: (output.internal_next_steps || []).length + " tindakan" },
    ], output.reasoning);
  } else {
    body.textContent = output.reasoning || JSON.stringify(output, null, 2);
  }
}

traces.forEach(step => {
  const body = {};
  try {
    formatTraceBody(step, body);
    console.log("SUCCESS:", step.agent);
  } catch (e) {
    console.log("CRASH ON:", step.agent, e.message);
  }
});
