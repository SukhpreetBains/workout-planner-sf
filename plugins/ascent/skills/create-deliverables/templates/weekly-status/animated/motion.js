import { animate, stagger } from '../assets/anime.esm.min.js';

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
if (!reduced.matches) {
  document.body.classList.add('motion-ready');

  function enter(page) {
    if (!page) return;
    const targets = [...page.querySelectorAll('h1,h2,.eyebrow,.lead,.health,.cover-art,.summary-art,.section-art,.card,.timeline-note')];
    if (targets.length) {
      animate(targets, {
        opacity: [0, 1],
        y: [24, 0],
        delay: stagger(75),
        duration: 620,
        ease: 'outExpo'
      });
    }
    const rail = page.querySelector('.timeline-rail');
    if (rail) animate(rail, { scaleY: [0, 1], duration: 850, ease: 'outExpo' });
    const checkpoints = [...page.querySelectorAll('.checkpoint')];
    if (checkpoints.length) {
      animate(checkpoints, { opacity: [0, 1], x: [-16, 0], delay: stagger(110), duration: 650, ease: 'outExpo' });
    }
  }

  document.addEventListener('reportpagechange', event => enter(event.detail.page));
  enter(document.querySelector('.page.active'));

  document.addEventListener('pointerenter', event => {
    const card = event.target.closest && event.target.closest('.card');
    if (card && card.closest('.page.active')) {
      animate(card, { scale: [1, 1.015], duration: 250, ease: 'outQuad' });
    }
  }, true);
  document.addEventListener('pointerleave', event => {
    const card = event.target.closest && event.target.closest('.card');
    if (card && card.closest('.page.active')) {
      animate(card, { scale: [1.015, 1], duration: 250, ease: 'outQuad' });
    }
  }, true);
}
