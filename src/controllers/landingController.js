export function attachLandingInteractions() {
  const tabs = [...document.querySelectorAll('[data-mf-tab]')];
  const select = tab => {
    tabs.forEach(item => {
      const active = item === tab;
      item.setAttribute('aria-selected', String(active));
      item.tabIndex = active ? 0 : -1;
    });
    document.querySelectorAll('[data-mf-panel]').forEach(panel => {
      panel.hidden = panel.dataset.mfPanel !== tab.dataset.mfTab;
    });
  };
  tabs.forEach((tab, index) => {
    tab.onclick = () => select(tab);
    tab.onkeydown = event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      select(tabs[next]);
      tabs[next].focus();
    };
  });
}
