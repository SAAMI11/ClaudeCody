/**
 * api.js - thin wrapper around SAAMai's REST API. Every backend call the
 * UI makes goes through here so the rest of the frontend never touches
 * fetch() URLs or auth headers directly.
 */

const SAAMaiAPI = (() => {
  const TOKEN_KEY = "saamai_token";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setToken(token) {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  }

  function authHeaders() {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function request(path, options = {}) {
    const resp = await fetch(path, {
      ...options,
      headers: { ...(options.headers || {}), ...authHeaders() },
    });
    if (!resp.ok) {
      let detail = resp.statusText;
      try {
        const data = await resp.json();
        detail = data.detail || detail;
      } catch (_) {
        /* body wasn't JSON - keep statusText */
      }
      throw new Error(detail);
    }
    return resp;
  }

  async function requestJSON(path, options = {}) {
    const resp = await request(path, options);
    if (resp.status === 204) return null;
    return resp.json();
  }

  return {
    getToken,
    setToken,

    // --- Auth ---
    login: (username, password) =>
      requestJSON("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      }),
    register: (username, password) =>
      requestJSON("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      }),
    me: () => requestJSON("/api/auth/me"),

    // --- Chats ---
    listChats: (q) => requestJSON(`/api/chats${q ? `?q=${encodeURIComponent(q)}` : ""}`),
    createChat: (payload = {}) =>
      requestJSON("/api/chats", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    getChat: (id) => requestJSON(`/api/chats/${id}`),
    updateChat: (id, payload) =>
      requestJSON(`/api/chats/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    deleteChat: (id) => request(`/api/chats/${id}`, { method: "DELETE" }),
    exportChatUrl: (id, format) => `/api/chats/${id}/export?format=${format}`,

    // --- Messages (streaming) ---
    async sendMessageStream(chatId, content, attachmentIds, onToken) {
      const resp = await request(`/api/chats/${chatId}/messages/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, attachment_ids: attachmentIds || [] }),
      });
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let full = "";
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        full += chunk;
        onToken(chunk, full);
      }
      return full;
    },

    // --- Documents ---
    async uploadDocument(file) {
      const form = new FormData();
      form.append("file", file);
      const resp = await request("/api/documents/upload", { method: "POST", body: form });
      return resp.json();
    },

    // --- Models ---
    listModels: () => requestJSON("/api/models"),
    async pullModel(name, onProgress) {
      const resp = await request("/api/models/pull", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();
        for (const line of lines) {
          if (line.trim()) onProgress(JSON.parse(line));
        }
      }
    },

    // --- Settings ---
    listSettings: () => requestJSON("/api/settings"),
    putSetting: (key, value) =>
      requestJSON("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, value }),
      }),

    // --- Plugins ---
    listPlugins: () => requestJSON("/api/plugins"),

    // --- i18n ---
    getTranslations: (lang) => requestJSON(`/api/i18n/${lang}`),
  };
})();
