/**
 * app.js - application bootstrap: wires the sidebar (chat list, search,
 * new chat), the composer (send, attach, voice) and the header actions
 * (model select, pin, export, delete) together, using SAAMaiAPI /
 * SAAMaiChat / SAAMaiSettings / SAAMaiI18n / SAAMaiVoice underneath.
 */

(function initApp() {
  const els = {};
  let chats = [];
  let activeChatId = null;

  function bindElements() {
    els.sidebar = document.getElementById("sidebar");
    els.sidebarToggle = document.getElementById("sidebarToggle");
    els.newChatBtn = document.getElementById("newChatBtn");
    els.searchInput = document.getElementById("searchInput");
    els.chatList = document.getElementById("chatList");
    els.composer = document.getElementById("composer");
    els.messageInput = document.getElementById("messageInput");
    els.attachBtn = document.getElementById("attachBtn");
    els.fileInput = document.getElementById("fileInput");
    els.micBtn = document.getElementById("micBtn");
    els.modelSelect = document.getElementById("modelSelect");
    els.pinBtn = document.getElementById("pinBtn");
    els.exportBtn = document.getElementById("exportBtn");
    els.deleteChatBtn = document.getElementById("deleteChatBtn");
  }

  function renderChatList(list) {
    els.chatList.innerHTML = "";
    if (list.length === 0) {
      const div = document.createElement("div");
      div.className = "chat-list-empty";
      div.dataset.i18n = "sidebar.noChats";
      div.textContent = SAAMaiI18n.t("sidebar.noChats");
      els.chatList.appendChild(div);
      return;
    }
    list.forEach((chat) => {
      const item = document.createElement("div");
      item.className = `chat-item${chat.id === activeChatId ? " active" : ""}`;
      item.dataset.id = chat.id;

      const pin = document.createElement("span");
      pin.className = "pin-indicator";
      pin.textContent = chat.pinned ? "📌" : "";

      const title = document.createElement("span");
      title.className = "title";
      title.textContent = chat.title;

      const del = document.createElement("button");
      del.className = "del-btn";
      del.textContent = "✕";
      del.title = SAAMaiI18n.t("chat.delete");
      del.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteChat(chat.id);
      });

      item.appendChild(pin);
      item.appendChild(title);
      item.appendChild(del);
      item.addEventListener("click", () => openChat(chat.id));
      els.chatList.appendChild(item);
    });
  }

  async function loadChatList(query) {
    chats = await SAAMaiAPI.listChats(query);
    renderChatList(chats);
  }

  async function openChat(id) {
    activeChatId = id;
    const chat = await SAAMaiAPI.getChat(id);
    SAAMaiChat.renderChat(chat);
    SAAMaiChat.clearAttachments();
    if (els.modelSelect.querySelector(`option[value="${chat.model}"]`)) {
      els.modelSelect.value = chat.model;
    }
    renderChatList(chats);
    if (window.innerWidth <= 860) els.sidebar.classList.remove("open");
  }

  async function newChat() {
    const chat = await SAAMaiAPI.createChat({ model: els.modelSelect.value || undefined });
    await loadChatList();
    await openChat(chat.id);
  }

  async function deleteChat(id) {
    if (!confirm("Chat wirklich löschen?")) return;
    await SAAMaiAPI.deleteChat(id);
    await loadChatList();
    if (activeChatId === id) {
      activeChatId = null;
      if (chats.length) await openChat(chats[0].id);
      else await newChat();
    }
  }

  async function togglePin() {
    const chat = SAAMaiChat.getCurrentChat();
    if (!chat) return;
    await SAAMaiAPI.updateChat(chat.id, { pinned: !chat.pinned });
    await loadChatList();
    await openChat(chat.id);
  }

  function exportChat() {
    const chat = SAAMaiChat.getCurrentChat();
    if (!chat) return;
    const format = (prompt("Format? (md / txt / json)", "md") || "md").trim().toLowerCase();
    window.open(SAAMaiAPI.exportChatUrl(chat.id, format), "_blank");
  }

  async function onModelChange() {
    const chat = SAAMaiChat.getCurrentChat();
    if (!chat) return;
    await SAAMaiAPI.updateChat(chat.id, { model: els.modelSelect.value });
  }

  function autoGrowTextarea() {
    els.messageInput.style.height = "auto";
    els.messageInput.style.height = `${Math.min(els.messageInput.scrollHeight, 200)}px`;
  }

  function initVoiceButton() {
    if (!SAAMaiVoice.speechInputSupported()) {
      els.micBtn.style.display = "none";
      return;
    }
    els.micBtn.addEventListener("click", () => {
      if (SAAMaiVoice.isListening()) {
        SAAMaiVoice.stopListening();
        return;
      }
      els.micBtn.classList.add("recording");
      SAAMaiVoice.startListening({
        lang: SAAMaiI18n.currentLang(),
        onResult: (text) => {
          els.messageInput.value = text;
          autoGrowTextarea();
        },
        onEnd: () => els.micBtn.classList.remove("recording"),
        onError: () => els.micBtn.classList.remove("recording"),
      });
    });
  }

  function bindEvents() {
    els.newChatBtn.addEventListener("click", newChat);
    els.sidebarToggle.addEventListener("click", () => els.sidebar.classList.toggle("open"));

    let searchDebounce;
    els.searchInput.addEventListener("input", () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => loadChatList(els.searchInput.value.trim()), 250);
    });

    els.composer.addEventListener("submit", (e) => {
      e.preventDefault();
      SAAMaiChat.sendCurrentMessage();
    });
    els.messageInput.addEventListener("input", autoGrowTextarea);
    els.messageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        SAAMaiChat.sendCurrentMessage();
      }
    });

    els.attachBtn.addEventListener("click", () => els.fileInput.click());
    els.fileInput.addEventListener("change", () => {
      if (els.fileInput.files.length) SAAMaiChat.addFiles(els.fileInput.files);
      els.fileInput.value = "";
    });

    els.pinBtn.addEventListener("click", togglePin);
    els.exportBtn.addEventListener("click", exportChat);
    els.deleteChatBtn.addEventListener("click", () => {
      const chat = SAAMaiChat.getCurrentChat();
      if (chat) deleteChat(chat.id);
    });
    els.modelSelect.addEventListener("change", onModelChange);

    document.addEventListener("saamai:chat-updated", () => loadChatList(els.searchInput.value.trim()));

    initVoiceButton();
  }

  async function bootstrap() {
    bindElements();
    SAAMaiChat.bindElements();
    SAAMaiSettings.init();
    bindEvents();

    await SAAMaiI18n.load(SAAMaiI18n.currentLang());
    try {
      await SAAMaiSettings.refreshModels();
    } catch (_) {
      /* Ollama might not be running yet - settings dialog will surface the error */
    }

    await loadChatList();
    if (chats.length > 0) {
      await openChat(chats[0].id);
    } else {
      await newChat();
    }
  }

  document.addEventListener("DOMContentLoaded", bootstrap);
})();
