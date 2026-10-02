(() => {
  // Native details provides keyboard and no-JavaScript access. Escape closes
  // the active module's source list and restores focus to its control.
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const disclosure = document.activeElement?.closest('.source-disclosure');
    if (!disclosure?.open) return;
    disclosure.open = false;
    disclosure.querySelector('summary').focus();
  });
})();
