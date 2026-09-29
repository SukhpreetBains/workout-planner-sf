(() => {
  const regions = [...document.querySelectorAll('.citation-region')];
  if (!regions.length) return;
  const mobile = () => matchMedia('(max-width:760px)').matches;
  let frame;

  function layout() {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => {
      if (mobile()) return;
      for (const region of regions) {
        const top = region.getBoundingClientRect().top;
        let previousBottom = 0;
        for (const note of region.querySelectorAll('.source-note')) {
          const target = note.dataset.citationTarget;
          const anchor = target === 'section' ? region.querySelector('.section') : region.querySelector(`[data-citation-anchor="${target}"]`);
          if (!anchor) continue;
          const y = Math.max(24, anchor.getBoundingClientRect().top - top, previousBottom + 10);
          note.style.setProperty('--source-top', `${Math.round(y)}px`);
          previousBottom = y + note.querySelector('summary').offsetHeight;
        }
      }
    });
  }

  function highlight(region) {
    region.querySelectorAll('.citation-highlight').forEach(el => el.classList.remove('citation-highlight'));
    for (const note of region.querySelectorAll('.source-note[open]')) {
      const target = note.dataset.citationTarget;
      const anchor = target === 'section' ? region.querySelector('.section') : region.querySelector(`[data-citation-anchor="${target}"]`);
      anchor?.classList.add('citation-highlight');
    }
    region.classList.toggle('citation-region--open', Boolean(region.querySelector('.source-note[open]')));
  }

  for (const region of regions) {
    for (const note of region.querySelectorAll('.source-note')) {
      note.addEventListener('toggle', () => {
        if (note.open) {
          region.querySelectorAll('.source-note[open]').forEach(other => { if (other !== note) other.open = false; });
        }
        highlight(region);
        layout();
      });
      note.querySelector('.source-panel__close').addEventListener('click', () => {
        note.open = false;
        note.querySelector('summary').focus();
      });
    }
    new ResizeObserver(layout).observe(region.querySelector('.citation-content'));
  }
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const note = document.activeElement.closest('.source-note');
    if (note?.open) {
      note.open = false;
      note.querySelector('summary').focus();
    }
  });
  document.documentElement.classList.add('citations-ready');
  window.addEventListener('resize', layout);
  document.fonts.ready.then(layout);
  window.addEventListener('load', layout);
  layout();
})();
