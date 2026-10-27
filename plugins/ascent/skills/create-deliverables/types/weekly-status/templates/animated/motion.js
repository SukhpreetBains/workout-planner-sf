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
    const dots = [...page.querySelectorAll('.ms-dot')];
    if (dots.length) {
      animate(dots, { scale: [0, 1], delay: stagger(90, { start: 200 }), duration: 520, ease: 'outBack' });
      animate(page.querySelectorAll('.ms-date-text'), { opacity: [0, 1], y: [-8, 0], delay: stagger(90, { start: 320 }), duration: 520, ease: 'outExpo' });
    }
  }

  document.addEventListener('reportpagechange', event => enter(event.detail.page));
  enter(document.querySelector('.page.active'));

  // The beam narrows to the open date at the top and spans the panel at the bottom.
  let beamX = null;
  document.addEventListener('milestonechange', event => {
    const root = event.target;
    const beam = root.querySelector('.ms-beam');
    const { previous, current, panel } = event.detail;
    if (!beam || current < 0) return;
    const width = root.querySelector('.ms-stage').getBoundingClientRect().width;
    const x = parseFloat(root.style.getPropertyValue('--ms-x'));
    const shape = previous < 0 ? { x, left: x, right: x } : { x: beamX === null ? x : beamX, left: 0, right: width };
    const draw = () => { beam.style.clipPath = `polygon(${shape.x - 7}px 0, ${shape.x + 7}px 0, ${shape.right}px 100%, ${shape.left}px 100%)`; };
    draw();
    animate(shape, { x, left: 0, right: width, duration: 560, ease: 'outExpo', onUpdate: draw, onComplete: () => { beam.style.clipPath = ''; } });
    beamX = x;
    const contents = panel.querySelectorAll('.icon,.ms-kicker,.ms-title,.detail,.citations');
    animate(contents, { opacity: [0, 1], y: [10, 0], delay: stagger(50, { start: previous < 0 ? 260 : 80 }), duration: 420, ease: 'outExpo' });
  });

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
