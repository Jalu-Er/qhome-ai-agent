const mode = document.querySelector("#mode");
const customerName = document.querySelector("#customerName");
const message = document.querySelector("#message");
const runButton = document.querySelector("#runButton");
const resetButton = document.querySelector("#resetButton");
const statusBox = document.querySelector("#status");
const chatThread = document.querySelector("#chatThread");
const intent = document.querySelector("#intent");
const priority = document.querySelector("#priority");
const escalate = document.querySelector("#escalate");
const ticketStatus = document.querySelector("#ticketStatus");
const team = document.querySelector("#team");
const runId = document.querySelector("#runId");
const missingInfo = document.querySelector("#missingInfo");
const nextSteps = document.querySelector("#nextSteps");
const trace = document.querySelector("#trace");

let history = [];

document.querySelectorAll("[data-sample]").forEach((button) => {
  button.addEventListener("click", () => {
    message.value = button.dataset.sample;
    message.focus();
  });
});

resetButton.addEventListener("click", () => {
  history = [];
  renderChat();
  renderEmptyPanel();
  setStatus("idle", "Staff triage panel siap.");
});

runButton.addEventListener("click", sendMessage);
message.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    sendMessage();
  }
});

renderChat();
renderEmptyPanel();

async function sendMessage() {
  const text = message.value.trim();
  if (!text) return;

  const priorHistory = [...history];
  history.push({ role: "customer", content: text });
  renderChat();
  message.value = "";
  setStatus("loading", "Menjalankan 5 agent untuk update triage...");
  runButton.disabled = true;

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: mode.value,
        customer_name: customerName.value,
        message: text,
        history: priorHistory,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Workflow gagal.");
    }
    const final = data.final || {};
    history.push({ role: "assistant", content: final.customer_reply || "Baik, pesan Anda sudah diterima." });
    renderChat();
    renderPanel(data);
    setStatus("done", `Triage updated. Run ID: ${data.run_id}`);
  } catch (error) {
    history.push({ role: "assistant", content: `Maaf, workflow gagal: ${error.message}` });
    renderChat();
    setStatus("error", error.message);
  } finally {
    runButton.disabled = false;
  }
}

function renderChat() {
  chatThread.innerHTML = "";
  if (!history.length) {
    const empty = document.createElement("div");
    empty.className = "chat-empty";
    empty.textContent = "Belum ada percakapan. Pilih sample atau tulis pesan customer.";
    chatThread.append(empty);
    return;
  }

  history.forEach((item) => {
    const bubble = document.createElement("article");
    bubble.className = `bubble ${item.role}`;
    const label = document.createElement("span");
    label.textContent = item.role === "customer" ? customerName.value || "Customer" : "QHome AI";
    const content = document.createElement("p");
    content.textContent = item.content;
    bubble.append(label, content);
    chatThread.append(bubble);
  });
  chatThread.scrollTop = chatThread.scrollHeight;
}

function renderPanel(data) {
  const final = data.final || {};
  const outputs = data.agent_outputs || {};
  const classifier = outputs.intent_classifier || {};
  const priorityOutput = outputs.priority_escalation || {};

  intent.textContent = final.intent || "-";
  priority.textContent = final.priority || "-";
  escalate.textContent = String(final.escalate ?? "-");
  team.textContent = final.escalation_team || priorityOutput.escalation_team || "-";
  runId.textContent = data.run_id || "-";
  ticketStatus.textContent = inferStatus(final, classifier);

  renderList(missingInfo, classifier.missing_information || []);
  renderList(nextSteps, final.internal_next_steps || []);

  trace.innerHTML = "";
  (data.trace || []).forEach((step) => {
    const item = document.createElement("article");
    item.className = "trace-item";
    const title = document.createElement("h3");
    title.textContent = step.agent;
    const body = document.createElement("p");
    body.textContent = step.output?.reasoning || JSON.stringify(step.output);
    item.append(title, body);
    trace.append(item);
  });
}

function renderEmptyPanel() {
  intent.textContent = "-";
  priority.textContent = "-";
  escalate.textContent = "-";
  ticketStatus.textContent = "-";
  team.textContent = "-";
  runId.textContent = "-";
  missingInfo.innerHTML = "";
  nextSteps.innerHTML = "";
  trace.innerHTML = "";
}

function renderList(target, values) {
  target.innerHTML = "";
  const items = Array.isArray(values) ? values : [values].filter(Boolean);
  if (!items.length) {
    const item = document.createElement("li");
    item.textContent = "Tidak ada.";
    target.append(item);
    return;
  }
  items.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = typeof value === "string" ? value : JSON.stringify(value);
    target.append(item);
  });
}

function inferStatus(final, classifier) {
  const missing = classifier.missing_information || [];
  if (Array.isArray(missing) && missing.length) {
    return "waiting_customer_info";
  }
  if (final.escalate) {
    return "ready_for_staff_review";
  }
  return "resolved_or_advisory";
}

function setStatus(kind, text) {
  statusBox.className = `status ${kind}`;
  statusBox.textContent = text;
}
