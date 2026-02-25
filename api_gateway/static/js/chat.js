/**
 * Petclinic Chat Widget
 *
 * Floating chatbox with toggle, chat bubbles, marked.js markdown rendering,
 * API integration (POST /api/genai/chatclient), localStorage persistence,
 * and error fallback.
 */

(function () {
  "use strict";

  var STORAGE_KEY = "petclinic_chat_history";
  var API_ENDPOINT = "/api/genai/chatclient";

  var chatbox = document.getElementById("chatbox");
  var header = document.getElementById("chatbox-header");
  var messages = document.getElementById("chatbox-messages");
  var input = document.getElementById("chatbox-input");
  var sendBtn = document.getElementById("chatbox-send-btn");

  var chatHistory = [];

  /* ── localStorage helpers ──────────────────────────────── */

  function loadHistory() {
    try {
      var data = localStorage.getItem(STORAGE_KEY);
      if (data) {
        chatHistory = JSON.parse(data);
        for (var i = 0; i < chatHistory.length; i++) {
          renderBubble(chatHistory[i].text, chatHistory[i].role);
        }
      }
    } catch (e) {
      chatHistory = [];
    }
  }

  function saveHistory() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(chatHistory));
    } catch (e) {
      /* Ignore storage quota errors */
    }
  }

  /* ── Toggle expand / collapse ─────────────────────────── */

  function toggleChatbox() {
    chatbox.classList.toggle("expanded");
    if (chatbox.classList.contains("expanded")) {
      input.focus();
      scrollToBottom();
    }
  }

  header.addEventListener("click", toggleChatbox);

  /* ── Render a chat bubble (DOM only, no history mutation) ── */

  function renderBubble(text, role) {
    var bubble = document.createElement("div");
    bubble.classList.add("chat-bubble", role);

    if (role === "bot" && typeof marked !== "undefined") {
      bubble.innerHTML = marked.parse(text);
    } else {
      bubble.textContent = text;
    }

    messages.appendChild(bubble);
    scrollToBottom();
  }

  /* ── Append a chat bubble (updates history + DOM) ──────── */

  function appendMessage(text, role) {
    chatHistory.push({ text: text, role: role });
    saveHistory();
    renderBubble(text, role);
  }

  function scrollToBottom() {
    requestAnimationFrame(function () {
      messages.scrollTop = messages.scrollHeight;
    });
  }

  /* ── Send message ─────────────────────────────────────── */

  function sendMessage() {
    var query = input.value;
    if (!query.trim()) return;

    input.value = "";
    appendMessage(query, "user");

    fetch(API_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(query),
    })
      .then(function (response) {
        return response.text();
      })
      .then(function (responseText) {
        appendMessage(responseText, "bot");
      })
      .catch(function () {
        appendMessage("Chat is currently unavailable", "bot");
      });
  }

  sendBtn.addEventListener("click", sendMessage);

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  /* ── Load chat history on init ─────────────────────────── */

  loadHistory();

  /* ── Expose for external wiring ────────────────────────── */

  window.petclinicChat = {
    appendMessage: appendMessage,
    scrollToBottom: scrollToBottom,
  };
})();
