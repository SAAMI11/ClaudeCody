/**
 * chat.js - owns the currently open chat: rendering messages, sending
 * new ones (with streaming render), handling attachments and the
 * per-chat toolbar actions (pin / export / delete).
 */

const SAAMaiChat = (() => {
  let currentChat = null; // full chat detail from the API
  let pendingAttachments = []; // [{id, filename, file_type}]

  const els = {};

  function bindElements() {
    els.messages = document.getElementById("messages");
    els.emptyState = document.getElementById("emptyState");
    els.chatTitle = document.getElementById("chatTitle");
    els.composer = document.getElementById("composer");
    els.input = document.getElementById("messageInput");
    els.attachmentPreview = document.getElementById("attachmentPreview");
    els.fileInput = document.getElementById("fileInput");
    els.pinBtn = document.getElementById("pinBtn");
  }

  function renderAttachmentIcon(type) {
    return { image: "🖼", pdf: "📄", docx: "📝", text: "📃" }[type] || "📎";
  }

  function appendMessageEl(role, content, attachments = []) {
    els.emptyState.style.display = "none";
    const wrap = document.createElement("div");
    wrap.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "🧑" : "🤖";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = content;

    const col = document.createElement("div");
    col.style.display = "flex";
    col.style.flexDirection = "column";
    col.appendChild(bubble);

    if (attachments.length) {
      const attWrap = document.createElement("div");
      attWrap.className = "attachments";
      attachments.forEach((a) => {
        const chip = document.createElement("span");
        chip.className = "attachment-chip";
        chip.textContent = `${renderAttachmentIcon(a.file_type)} ${a.filename}`;
        attWrap.appendChild(chip);
      });
      col.appendChild(attWrap);
    }

    if (role === "assistant" && SAAMaiVoice.speechOutputSupported()) {
      const speakBtn = document.createElement("button");
      speakBtn.className = "speak-btn";
      speakBtn.textContent = "🔊 " + SAAMaiI18n.t("chat.speak", "Vorlesen");
      speakBtn.type = "button";
      speakBtn.addEventListener("click", () => SAAMaiVoice.speak(bubble.textContent, SAAMaiI18n.currentLang()));
      col.appendChild(speakBtn);
    }

    wrap.appendChild(avatar);
    wrap.appendChild(col);
    els.messages.appendChild(wrap);
    els.messages.scrollTop = els.messages.scrollHeight;
    return bubble;
  }

  function renderChat(chat) {
    currentChat = chat;
    els.messages.innerHTML = "";
    els.messages.appendChild(els.emptyState);
    els.chatTitle.textContent = chat.title;
    els.pinBtn.style.opacity = chat.pinned ? 1 : 0.5;

    if (chat.messages.length === 0) {
      els.emptyState.style.display = "flex";
    } else {
      chat.messages.forEach((m) => appendMessageEl(m.role, m.content, m.attachments));
    }
  }

  function clearAttachments() {
    pendingAttachments = [];
    renderAttachmentPreview();
  }

  function renderAttachmentPreview() {
    els.attachmentPreview.innerHTML = "";
    pendingAttachments.forEach((att) => {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.innerHTML = `<span>${renderAttachmentIcon(att.file_type)} ${att.filename}</span>`;
      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.textContent = "✕";
      removeBtn.addEventListener("click", () => {
        pendingAttachments = pendingAttachments.filter((a) => a.id !== att.id);
        renderAttachmentPreview();
      });
      chip.appendChild(removeBtn);
      els.attachmentPreview.appendChild(chip);
    });
  }

  async function addFiles(fileList) {
    for (const file of Array.from(fileList)) {
      try {
        const attachment = await SAAMaiAPI.uploadDocument(file);
        pendingAttachments.push(attachment);
      } catch (err) {
        alert(`${file.name}: ${err.message}`);
      }
    }
    renderAttachmentPreview();
  }

  async function sendCurrentMessage() {
    if (!currentChat) return;
    const text = els.input.value.trim();
    if (!text && pendingAttachments.length === 0) return;

    els.input.value = "";
    els.input.style.height = "auto";
    const attachmentIds = pendingAttachments.map((a) => a.id);
    const attachmentsForDisplay = pendingAttachments;
    clearAttachments();

    appendMessageEl("user", text, attachmentsForDisplay);
    const assistantBubble = appendMessageEl("assistant", "");
    assistantBubble.classList.add("streaming");

    try {
      await SAAMaiAPI.sendMessageStream(currentChat.id, text, attachmentIds, (_chunk, full) => {
        assistantBubble.textContent = full;
        els.messages.scrollTop = els.messages.scrollHeight;
      });
    } catch (err) {
      assistantBubble.textContent = SAAMaiI18n.t("error.llmUnreachable");
    } finally {
      assistantBubble.classList.remove("streaming");
    }

    // Refresh in the background so title/updated_at changes reflect in the sidebar.
    document.dispatchEvent(new CustomEvent("saamai:chat-updated"));
  }

  function getCurrentChat() {
    return currentChat;
  }

  return {
    bindElements,
    renderChat,
    addFiles,
    sendCurrentMessage,
    getCurrentChat,
    clearAttachments,
  };
})();
