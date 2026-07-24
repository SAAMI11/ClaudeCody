/**
 * settings.js - the settings dialog: language, theme, local model
 * management (list/download), plugin overview and the optional local
 * account (login/register/logout).
 */

const SAAMaiSettings = (() => {
  const THEME_KEY = "saamai_theme";
  const els = {};

  function bindElements() {
    els.modal = document.getElementById("settingsModal");
    els.settingsBtn = document.getElementById("settingsBtn");
    els.themeToggleBtn = document.getElementById("themeToggleBtn");
    els.languageSelect = document.getElementById("languageSelect");
    els.segmentedBtns = Array.from(document.querySelectorAll(".segmented-btn"));
    els.modelList = document.getElementById("modelList");
    els.modelSelect = document.getElementById("modelSelect");
    els.pullModelName = document.getElementById("pullModelName");
    els.pullModelBtn = document.getElementById("pullModelBtn");
    els.pullProgress = document.getElementById("pullProgress");
    els.pluginList = document.getElementById("pluginList");
    els.accountLoggedOut = document.getElementById("accountLoggedOut");
    els.accountLoggedIn = document.getElementById("accountLoggedIn");
    els.accountUsername = document.getElementById("accountUsername");
    els.authUsername = document.getElementById("authUsername");
    els.authPassword = document.getElementById("authPassword");
    els.loginBtn = document.getElementById("loginBtn");
    els.registerBtn = document.getElementById("registerBtn");
    els.logoutBtn = document.getElementById("logoutBtn");
  }

  function currentTheme() {
    return localStorage.getItem(THEME_KEY) || "dark";
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
    els.themeToggleBtn.textContent = theme === "dark" ? "🌙" : "☀️";
    els.segmentedBtns.forEach((btn) => btn.classList.toggle("active", btn.dataset.theme === theme));
  }

  function toggleTheme() {
    applyTheme(currentTheme() === "dark" ? "light" : "dark");
    SAAMaiAPI.putSetting("theme", currentTheme()).catch(() => {});
  }

  async function refreshModels() {
    const result = await SAAMaiAPI.listModels();
    const models = Array.isArray(result) ? result : result.models || [];
    els.modelList.innerHTML = "";
    els.modelSelect.innerHTML = "";

    if (models.length === 0) {
      const li = document.createElement("li");
      li.textContent = result.error || "Keine Modelle gefunden.";
      els.modelList.appendChild(li);
    }

    models.forEach((m) => {
      const li = document.createElement("li");
      li.textContent = m.name;
      els.modelList.appendChild(li);

      const opt = document.createElement("option");
      opt.value = m.name;
      opt.textContent = m.name;
      els.modelSelect.appendChild(opt);
    });
    return models;
  }

  async function pullModel() {
    const name = els.pullModelName.value.trim();
    if (!name) return;
    els.pullModelBtn.disabled = true;
    els.pullProgress.textContent = `Lade ${name}...`;
    try {
      await SAAMaiAPI.pullModel(name, (event) => {
        els.pullProgress.textContent = event.status || JSON.stringify(event);
      });
      els.pullProgress.textContent = `${name} bereit.`;
      await refreshModels();
    } catch (err) {
      els.pullProgress.textContent = `Fehler: ${err.message}`;
    } finally {
      els.pullModelBtn.disabled = false;
    }
  }

  async function refreshPlugins() {
    try {
      const plugins = await SAAMaiAPI.listPlugins();
      els.pluginList.innerHTML = "";
      if (plugins.length === 0) {
        const li = document.createElement("li");
        li.textContent = "Keine Plugins geladen.";
        els.pluginList.appendChild(li);
      }
      plugins.forEach((p) => {
        const li = document.createElement("li");
        li.innerHTML = `<span>${p.name}</span>`;
        li.title = p.description;
        els.pluginList.appendChild(li);
      });
    } catch (_) {
      /* plugin listing is best-effort */
    }
  }

  async function refreshAccount() {
    try {
      const user = await SAAMaiAPI.me();
      const loggedIn = !!SAAMaiAPI.getToken();
      els.accountLoggedOut.hidden = loggedIn;
      els.accountLoggedIn.hidden = !loggedIn;
      els.accountUsername.textContent = user.username;
    } catch (_) {
      els.accountLoggedOut.hidden = false;
      els.accountLoggedIn.hidden = true;
    }
  }

  async function login() {
    try {
      const result = await SAAMaiAPI.login(els.authUsername.value, els.authPassword.value);
      SAAMaiAPI.setToken(result.access_token);
      await refreshAccount();
    } catch (err) {
      alert(err.message);
    }
  }

  async function register() {
    try {
      const result = await SAAMaiAPI.register(els.authUsername.value, els.authPassword.value);
      SAAMaiAPI.setToken(result.access_token);
      await refreshAccount();
    } catch (err) {
      alert(err.message);
    }
  }

  function logout() {
    SAAMaiAPI.setToken(null);
    refreshAccount();
  }

  async function open() {
    els.modal.showModal();
    refreshModels();
    refreshPlugins();
    refreshAccount();
  }

  function init() {
    bindElements();
    applyTheme(currentTheme());

    els.settingsBtn.addEventListener("click", open);
    els.themeToggleBtn.addEventListener("click", toggleTheme);
    els.segmentedBtns.forEach((btn) =>
      btn.addEventListener("click", () => {
        applyTheme(btn.dataset.theme);
        SAAMaiAPI.putSetting("theme", btn.dataset.theme).catch(() => {});
      })
    );

    els.languageSelect.value = SAAMaiI18n.currentLang();
    els.languageSelect.addEventListener("change", () => {
      SAAMaiI18n.load(els.languageSelect.value);
      SAAMaiAPI.putSetting("language", els.languageSelect.value).catch(() => {});
    });

    els.pullModelBtn.addEventListener("click", pullModel);
    els.loginBtn.addEventListener("click", login);
    els.registerBtn.addEventListener("click", register);
    els.logoutBtn.addEventListener("click", logout);
  }

  return { init, refreshModels, currentTheme };
})();
