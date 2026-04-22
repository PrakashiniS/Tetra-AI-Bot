const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const pauseBtn = document.getElementById("pause-btn");
const chatContainer = document.getElementById("chat-container");

let typingPaused = false;
let typingInterval;

/* ===============================
   AVATAR MESSAGE STRUCTURE
================================= */
function appendMessage(html, sender) {
  const row = document.createElement("div");
  row.className = "chat-row " + sender;

  const avatar = document.createElement("div");
  avatar.className = "chat-avatar " + sender;
  avatar.innerHTML = sender === "assistant" ? "🤖" : "👤";

  const bubble = document.createElement("div");
  bubble.className = "chat-bubble " + sender;
  bubble.innerHTML = html;

  // 🤖 Assistant → LEFT (Avatar first)
  if (sender === "assistant") {
    row.appendChild(avatar);
    row.appendChild(bubble);
  }

  // 👤 User → RIGHT (Bubble first, Avatar last)
  if (sender === "user") {
    row.appendChild(bubble);
    row.appendChild(avatar);
  }

  chatContainer.appendChild(row);
  chatContainer.scrollTop = chatContainer.scrollHeight;

  return bubble;
}

/* ===============================
   SEND MESSAGE
================================= */
async function sendMessage() {
  const userQuery = input.value.trim();
  if (!userQuery) return;

  appendMessage(escapeHtml(userQuery), "user");
  input.value = "";

  showTyping();

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: userQuery }),
    });

    const data = await res.json();
    removeTyping();
    typeResponse(data.response || "No response received.");
  } catch (e) {
    removeTyping();
    typeResponse("Network error. Is the server running?");
  }
}

/* ===============================
   TYPING EFFECT
================================= */
function typeResponse(text) {
  const bubble = appendMessage("", "assistant");

  const htmlContent = marked.parse(text);
  const tempDiv = document.createElement("div");
  tempDiv.innerHTML = htmlContent;
  const fullText = tempDiv.innerHTML;

  let index = 0;

  clearInterval(typingInterval);
  typingPaused = false;

  typingInterval = setInterval(() => {
    if (!typingPaused && index < fullText.length) {
      bubble.innerHTML = fullText.substring(0, index);
      chatContainer.scrollTop = chatContainer.scrollHeight;
      index++;
    } else if (index >= fullText.length) {
      clearInterval(typingInterval);
    }
  }, 8);
}

/* ===============================
   TYPING INDICATOR
================================= */
function showTyping() {
  const row = document.createElement("div");
  row.className = "chat-row assistant typing-msg";

  const avatar = document.createElement("div");
  avatar.className = "chat-avatar assistant";
  avatar.innerHTML = "🤖";

  const bubble = document.createElement("div");
  bubble.className = "chat-bubble assistant";
  bubble.innerHTML = `
    <div class="typing">
      <span></span>
      <span></span>
      <span></span>
    </div>
  `;

  row.appendChild(avatar);
  row.appendChild(bubble);

  chatContainer.appendChild(row);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeTyping() {
  const typing = document.querySelector(".typing-msg");
  if (typing) typing.remove();
}

/* ===============================
   ESCAPE HTML
================================= */
function escapeHtml(unsafe) {
  return unsafe.replaceAll("&","&amp;")
               .replaceAll("<","&lt;")
               .replaceAll(">","&gt;")
               .replaceAll('"',"&quot;")
               .replaceAll("'","&#039;");
}

/* ===============================
   PAUSE BUTTON
================================= */
pauseBtn?.addEventListener("click", () => {
  typingPaused = !typingPaused;
  pauseBtn.textContent = typingPaused ? "▶️" : "⏸";
  pauseBtn.setAttribute("aria-pressed", String(typingPaused));
});

/* ===============================
   EVENTS
================================= */
sendBtn?.addEventListener("click", sendMessage);

input?.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
window.addEventListener("DOMContentLoaded", () => {
  if (typeof alertify !== "undefined" && typeof loggedInUser !== "undefined") {

    alertify.set('notifier','position', 'top-right');

    alertify.success(
      `Welcome ${loggedInUser} 👋`,
      4
    );

  }
});
