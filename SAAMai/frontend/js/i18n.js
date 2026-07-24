/**
 * i18n.js - loads a translation JSON file and applies it to every
 * element tagged with data-i18n / data-i18n-placeholder / data-i18n-title.
 * Adding a new language only ever requires a new frontend/locales/xx.json
 * file - nothing here needs to change.
 */

const SAAMaiI18n = (() => {
  const LANG_KEY = "saamai_language";
  let current = {};

  function currentLang() {
    return localStorage.getItem(LANG_KEY) || (navigator.language || "de").slice(0, 2);
  }

  async function load(lang) {
    try {
      const resp = await fetch(`locales/${lang}.json`);
      current = resp.ok ? await resp.json() : {};
    } catch (_) {
      current = {};
    }
    localStorage.setItem(LANG_KEY, lang);
    document.documentElement.lang = lang;
    apply();
  }

  function t(key, fallback = key) {
    return current[key] ?? fallback;
  }

  function apply() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.dataset.i18n, el.textContent);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.placeholder = t(el.dataset.i18nPlaceholder, el.placeholder);
    });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      el.title = t(el.dataset.i18nTitle, el.title);
    });
  }

  return { load, t, currentLang, apply };
})();
