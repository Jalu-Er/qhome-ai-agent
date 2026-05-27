/* QHome Customer Chat */

const chatThread = document.getElementById("chatThread");
const customerName = document.getElementById("customerName");
const message = document.getElementById("message");
const sendBtn = document.getElementById("sendBtn");
const mode = document.getElementById("mode");
const samplesRow = document.getElementById("samples");

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

  history.push({ role: "customer", content: text });
  renderChat();
  message.value = "";
  message.style.height = "auto";
  sendBtn.disabled = true;

  /* Hide samples after first message */
  samplesRow.hidden = true;

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
  } catch (err) {
    history.push({ role: "assistant", content: "Maaf, terjadi gangguan: " + err.message });
  }
  renderChat();
  sendBtn.disabled = false;
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
    p.textContent = item.content;
    div.append(label, p);
    chatThread.append(div);
  });
  chatThread.scrollTop = chatThread.scrollHeight;
}
