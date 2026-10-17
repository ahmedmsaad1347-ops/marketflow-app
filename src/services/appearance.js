import { icon } from '../views/ui.js';

// Appearance is a device preference and survives account sign-out.
const KEY = 'marketflow:theme';
let activeTheme = 'dark';
let initialized = false;

export function currentTheme() { return activeTheme; }

export function syncAppearanceControls() {
  document.querySelectorAll('[data-theme-choice]').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.themeChoice === activeTheme));
  });
  const toggle = document.querySelector('#workspaceThemeToggle');
  if (toggle) {
    toggle.innerHTML = icon(activeTheme === 'dark' ? 'sun' : 'moon');
    toggle.setAttribute('aria-label', `Switch to ${activeTheme === 'dark' ? 'light' : 'dark'} mode`);
    toggle.title = `Switch to ${activeTheme === 'dark' ? 'Light' : 'Deep Blue'}`;
  }
}

export function setTheme(theme, { persist = true } = {}) {
  if (!['light', 'dark'].includes(theme)) return;
  activeTheme = theme;
  document.documentElement.dataset.mfTheme = theme;
  if (persist) {
    try { localStorage.setItem(KEY, theme); } catch { /* The current session still supports switching. */ }
  }
  if (document.documentElement.dataset.workspace === 'true') {
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#0b1530' : '#f3f6fc');
  }
  syncAppearanceControls();
  document.dispatchEvent(new CustomEvent('marketflow:appearancechange', { detail: { theme } }));
}

export function initializeAppearance() {
  if (initialized) return;
  initialized = true;
  let saved;
  try { saved = localStorage.getItem(KEY); } catch { /* Private storage may be unavailable. */ }
  setTheme(saved === 'light' ? 'light' : 'dark', { persist: false });
  document.addEventListener('click', event => {
    const choice = event.target.closest('[data-theme-choice]');
    if (choice) setTheme(choice.dataset.themeChoice);
    if (event.target.closest('#workspaceThemeToggle')) setTheme(activeTheme === 'dark' ? 'light' : 'dark');
  });
  window.addEventListener('storage', event => {
    if (event.key === KEY) setTheme(event.newValue === 'light' ? 'light' : 'dark', { persist: false });
  });
}

export function setWorkspaceAppearance(enabled) {
  document.documentElement.dataset.workspace = String(enabled);
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', enabled ? (activeTheme === 'dark' ? '#0b1530' : '#f3f6fc') : '#0b0e14');
  if (!enabled) document.body.style.overflow = '';
}
