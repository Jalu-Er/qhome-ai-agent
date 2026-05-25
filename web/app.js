const mode = document.querySelector("#mode");
const customerName = document.querySelector("#customerName");
const message = document.querySelector("#message");
const runButton = document.querySelector("#runButton");
const statusBox = document.querySelector("#status");
const intent = document.querySelector("#intent");
const priority = document.querySelector("#priority");
const escalate = document.querySelector("#escalate");
const reply = document.querySelector("#reply");
const trace = document.querySelector("#trace");

document.querySelectorAll("[data-sample]").forEach((button) => {
  button.addEventListener("click", () => {
    message.value = button.dataset.sample;
  });
});

runButton.addEventListener("click", async () => {
  setStatus("loading", "Menjalankan 5 agent...");
  runButton.disabled = true;
  trace.innerHTML = "";

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: mode.value,
        customer_name: customerName.value,
        message: message.value,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Workflow gagal.");
    }
    renderResult(data);
    setStatus("done", `Selesai. Run ID: ${data.run_id}`);
  } catch (error) {
    setStatus("error", error.message);
  } finally {
    runButton.disabled = false;
  }
});

function renderResult(data) {
  const final = data.final || {};
  intent.textContent = final.intent || "-";
  priority.textContent = final.priority || "-";
  escalate.textContent = String(final.escalate ?? "-");
  reply.textContent = final.customer_reply || "-";
  reply.classList.remove("empty");

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

function setStatus(kind, text) {
  statusBox.className = `status ${kind}`;
  statusBox.textContent = text;
}
