const paths = {
  home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
  campaigns: '<rect x="3" y="6" width="18" height="15" rx="3"/><path d="M8 6V3h8v3M3 12h18m-11 0v3h4v-3"/>',
  spark: '<path d="m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4Z"/><path d="m20 2 .7 2.3L23 5l-2.3.7L20 8l-.7-2.3L17 5l2.3-.7Z"/>',
  chart: '<path d="M4 3v17h17M9 15v-4m5 4V6m5 9v-7"/>',
  message: '<path d="M21 11.5a8.3 8.3 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.3 8.3 0 0 1-3.8-.9L3 21l1.9-5.7a8.3 8.3 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.3 8.3 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z"/><path d="M8 11h8"/>',
  link: '<path d="m10 13 4-4m-6 6-2 2a3.5 3.5 0 0 1-5-5l4-4a3.5 3.5 0 0 1 5 0m4 0 2-2a3.5 3.5 0 0 1 5 5l-4 4a3.5 3.5 0 0 1-5 0" transform="translate(1 1)"/>',
  history: '<path d="M3 11a9 9 0 1 1 2.6 7M3 4v7h7m2-4v5l3 2"/>',
  settings: '<path d="m9 3-.6 2.5-2.2 1.3L3.7 6l-2 3.5 1.9 1.8v2.4l-1.9 1.8 2 3.5 2.5-.8 2.2 1.3L9 22h4l.6-2.5 2.2-1.3 2.5.8 2-3.5-1.9-1.8v-2.4l1.9-1.8-2-3.5-2.5.8-2.2-1.3L13 3Z" transform="translate(1 -1) scale(.95)"/><circle cx="11.5" cy="11.5" r="3"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9m-11 9a3 3 0 0 0 6 0"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  moon: '<path d="M20.7 13.2A9 9 0 0 1 10.8 3.3a9 9 0 1 0 9.9 9.9Z"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  shield: '<path d="m12 3 8 3v6c0 4-4 7-8 9-4-2-8-5-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Zm0 0v6h6M8 13h8m-8 4h5"/>',
  archive: '<rect x="3" y="3" width="18" height="4" rx="1"/><path d="M5 7v14h14V7m-10 5h6"/>',
  logout: '<path d="M9 4H4v16h5m5-12 4 4-4 4m-7-4h11"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c4 4 4 14 0 18-4-4-4-14 0-18"/>',
  circle: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5m0 3v.01"/>',
};

export function icon(name, className = '') {
  return `<svg class="mf-icon ${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.spark}</svg>`;
}

export function brandLogo({ compact = false } = {}) {
  return `<span class="mf-brand-lockup"><img src="/brand/marketflow-mark.png" width="40" height="40" alt="${compact ? 'MarketFlow' : ''}" class="mf-brand-image">${compact ? '' : '<span class="mf-wordmark">Market<span>Flow</span></span>'}</span>`;
}

export function themeChoices(className = '') {
  return `<div class="mf-theme-choices ${className}" role="group" aria-label="Color theme"><button type="button" data-theme-choice="light" aria-pressed="false">${icon('sun')}<span>Light</span></button><button type="button" data-theme-choice="dark" aria-pressed="false">${icon('moon')}<span>Deep Blue</span></button></div>`;
}
