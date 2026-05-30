/* QHome Customer Chat */

const chatThread = document.getElementById("chatThread");
const customerName = document.getElementById("customerName");
const message = document.getElementById("message");
const sendBtn = document.getElementById("sendBtn");
const mode = document.getElementById("mode");
const samplesRow = document.getElementById("samples");
const pipelineBadge = document.getElementById("pipelineBadge");

let history = [];
const sessionId = "CS-" + Math.random().toString(36).slice(2, 8);


/* Sample buttons */
document.querySelectorAll("[data-sample]").forEach((btn) => {
  btn.addEventListener("click", () => {
    message.value = btn.dataset.sample;
    message.focus();
  });
});

/* Send */
sendBtn.addEventListener("click", send);
message.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") send();
});

/* Auto-resize textarea */
message.addEventListener("input", () => {
  message.style.height = "auto";
  message.style.height = Math.min(message.scrollHeight, 120) + "px";
});

renderChat();

async function send() {
  const text = message.value.trim();
  const name = customerName.value.trim() || "Pelanggan";
  if (!text) return;

  // Lock customer name input after first message
  customerName.disabled = true;

  history.push({ role: "customer", content: text });
  renderChat();
  message.value = "";
  message.style.height = "auto";
  sendBtn.disabled = true;

  /* Hide samples after first message */
  samplesRow.hidden = true;

  // Append premium visual typing indicator
  const typingIndicator = document.createElement("div");
  typingIndicator.className = "bubble assistant";
  typingIndicator.id = "typingIndicator";
  typingIndicator.innerHTML = '<span class="bubble-name">QHome AI</span><div class="typing-dots"><span></span><span></span><span></span></div>';
  chatThread.appendChild(typingIndicator);
  chatThread.scrollTop = chatThread.scrollHeight;

  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        mode: mode.value,
        customer_name: name,
        message: text,
        history: history.slice(0, -1),
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Gagal memproses.");
    const reply = (data.final || {}).customer_reply || "Pesan Anda sudah diterima.";
    history.push({ role: "assistant", content: reply });
    // Update pipeline badge from triage_router output
    const pipeline = (data.agent_outputs || {}).triage_router?.selected_pipeline || null;
    updatePipelineBadge(pipeline);
  } catch (err) {
    history.push({ role: "assistant", content: "Maaf, terjadi gangguan: " + err.message });
  } finally {
    const indicator = document.getElementById("typingIndicator");
    if (indicator) indicator.remove();
    renderChat();
    sendBtn.disabled = false;
  }
}

function renderChat() {
  chatThread.innerHTML = "";
  if (!history.length) {
    chatThread.innerHTML =
      '<div class="chat-empty">' +
      '<svg width="40" height="40" viewBox="0 0 40 40" fill="none"><rect x="4" y="7" width="32" height="22" rx="4" stroke="currentColor" stroke-width="2"/><path d="M12 15h16M12 20h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M10 29l5-5h16" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
      "<p>Halo! Ada yang bisa kami bantu?</p>" +
      "<p class='chat-empty-sub'>Tanyakan tentang pesanan, produk, atau layanan QHome Mart.</p>" +
      "</div>";
    return;
  }
  const name = customerName.value.trim() || "Anda";
  history.forEach((item) => {
    const div = document.createElement("div");
    div.className = "bubble " + item.role;
    const label = document.createElement("span");
    label.className = "bubble-name";
    label.textContent = item.role === "customer" ? name : "QHome AI";
    const p = document.createElement("p");
    p.className = "bubble-text";

    // Parse basic markdown formatting
    let formatted = item.content
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    p.innerHTML = formatted;
    div.append(label, p);
    chatThread.append(div);
  });
  chatThread.scrollTop = chatThread.scrollHeight;
}

function updatePipelineBadge(pipeline) {
  if (!pipelineBadge || !pipeline) return;
  const prevPipeline = pipelineBadge.dataset.pipeline;
  pipelineBadge.dataset.pipeline = pipeline;
  pipelineBadge.classList.remove("hidden", "pipeline-support", "pipeline-renovation");
  if (pipeline === "renovation_quote") {
    pipelineBadge.textContent = "🏗️ Renovation Pipeline";
    pipelineBadge.classList.add("pipeline-renovation");
  } else {
    pipelineBadge.textContent = "🔧 Support Pipeline";
    pipelineBadge.classList.add("pipeline-support");
  }
  // Flash animation when pipeline changes
  if (prevPipeline && prevPipeline !== pipeline) {
    pipelineBadge.classList.add("pipeline-switch");
    setTimeout(() => pipelineBadge.classList.remove("pipeline-switch"), 800);
  }
}
