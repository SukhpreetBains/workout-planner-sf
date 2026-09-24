/**
 * motion.js — the motion vocabulary, over Anime.js v4.
 *
 * Components declare motion with a `data-motion` attribute. They never contain
 * animation code, and they are never hidden by CSS: everything on the page is
 * readable with JavaScript disabled or blocked. This file applies each
 * recipe's "before" state itself, immediately before animating it away.
 *
 * A client deliverable is not a marketing site. Motion here earns its place by
 * aiding comprehension: nothing loops, nothing parallaxes, nothing re-animates
 * on scroll back, and nothing carries meaning that the text does not.
 */

import { animate, createTimeline, onScroll, stagger, svg, utils } from 'animejs';

const D_FAST = 400;
const D_BASE = 600;
const D_LINE = 1200;

const prefersReduced = () =>
  typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Reveal once, never on scroll back. */
const revealOnce = () => onScroll({ once: true });

/**
 * Actions that force a recipe's end state. A recipe that rewrites real content
 * — count-up is the only one — registers here so printing can never capture a
 * half-finished number.
 */
const finalisers = new Set();

export function finaliseMotion() {
  for (const done of finalisers) {
    try { done(); } catch { /* a finaliser must never block the print */ }
  }
}

const $ = (root, sel) => Array.from(root.querySelectorAll(sel));

/* ==========================================================================
   RECIPES

   Keys are the permitted `data-motion` values. Each recipe receives the
   element that declared it. Keep one quoted key per line — the test suite
   reads this list to prove every `data-motion` the builder can emit has a
   recipe here.
   ========================================================================== */

export const RECIPES = {
  'fade-up': (el) => {
    utils.set(el, { opacity: 0, y: 24 });
    animate(el, {
      y: [24, 0], opacity: [0, 1],
      ease: 'outExpo', duration: D_BASE,
      autoplay: revealOnce(),
    });
  },

  'stagger-up': (el) => {
    const items = childItems(el);
    if (!items.length) return;
    utils.set(items, { opacity: 0, y: 24 });
    animate(items, {
      y: [24, 0], opacity: [0, 1],
      ease: 'outExpo', duration: D_BASE,
      delay: stagger(80),
      autoplay: onScroll({ target: el, once: true }),
    });
  },

  'color-bar-draw': (el) => {
    const swatches = $(el, '.color-bar__swatch');
    if (!swatches.length) return;
    utils.set(swatches, { scaleX: 0, transformOrigin: 'left center' });
    animate(swatches, {
      scaleX: [0, 1],
      ease: 'outExpo', duration: 500,
      delay: stagger(90), // in the fixed brand order, left to right
      autoplay: revealOnce(),
    });
  },

  'line-draw': (el) => {
    const paths = $(el, 'path');
    if (!paths.length) return;
    const drawables = svg.createDrawable(paths);
    animate(drawables, {
      draw: ['0 0', '0 1'],
      ease: 'inOutQuad', duration: D_LINE,
      autoplay: revealOnce(),
    });
  },

  'count-up': (el) => {
    const targets = $(el, '[data-count-to]');
    const items = childItems(el);
    if (items.length) {
      utils.set(items, { opacity: 0, y: 24 });
      animate(items, {
        y: [24, 0], opacity: [0, 1],
        ease: 'outExpo', duration: D_BASE,
        delay: stagger(80),
        autoplay: onScroll({ target: el, once: true }),
      });
    }
    // A non-numeric KPI degrades to a plain render — the builder simply omits
    // data-count-to, and nothing here has to know about it.
    for (const node of targets) {
      const to = Number(node.dataset.countTo);
      if (!Number.isFinite(to)) continue;
      const decimals = (node.dataset.countDecimals | 0) || 0;
      const format = new Intl.NumberFormat(undefined, {
        minimumFractionDigits: decimals, maximumFractionDigits: decimals,
      });
      const state = { n: 0 };
      // The real figure stays in the DOM until the animation actually starts.
      // Zeroing it here would print "0%" on any tile that had not been scrolled
      // to yet — the animation would be quietly destroying the content.
      finalisers.add(() => { node.textContent = format.format(to); });
      animate(state, {
        n: to,
        ease: 'outExpo', duration: 900,
        onUpdate: () => { node.textContent = format.format(state.n); },
        onComplete: () => { node.textContent = format.format(to); },
        autoplay: onScroll({ target: node, once: true }),
      });
    }
  },

  'cell-sweep': (el) => {
    const cells = $(el, '[data-cell]');
    if (!cells.length) return;
    const cols = Number(el.dataset.motionCols) || 1;
    const rows = Math.max(1, Math.ceil(cells.length / cols));
    utils.set(cells, { opacity: 0, x: -8 });
    animate(cells, {
      opacity: [0, 1], x: [-8, 0],
      ease: 'outQuad', duration: D_FAST,
      delay: stagger(40, { grid: [cols, rows], from: 'first' }),
      autoplay: onScroll({ target: el, once: true }),
    });
  },

  'path-draw': (el) => {
    const paths = $(el, '.roadmap__path path');
    const phases = $(el, '.phase');
    const tl = createTimeline({ autoplay: onScroll({ target: el, once: true }) });
    if (paths.length) {
      const drawables = svg.createDrawable(paths);
      tl.add(drawables, { draw: ['0 0', '0 1'], ease: 'inOutQuad', duration: 700 });
    }
    if (phases.length) {
      utils.set(phases, { opacity: 0, y: 24 });
      tl.add(phases, {
        y: [24, 0], opacity: [0, 1],
        ease: 'outExpo', duration: D_BASE, delay: stagger(80),
      }, paths.length ? '-=300' : 0);
    }
  },

  'execution-map-reveal': (el) => {
    const rows = $(el, '[data-motion-item]');
    if (!rows.length) return;
    utils.set(rows, { opacity: 0, x: -12 });
    animate(rows, {
      opacity: [0, 1], x: [-12, 0], ease: 'outExpo', duration: D_BASE,
      delay: stagger(70), autoplay: onScroll({ target: el, once: true }),
    });
  },

  'scroll-sync': (el) => {
    const fill = el.querySelector('.rail__fill');
    if (!fill) return;
    animate(fill, {
      scaleX: [0, 1],
      ease: 'linear',
      autoplay: onScroll({ target: document.documentElement, sync: true }),
    });
  },

  none: () => {},
};

export const MOTION_NAMES = Object.keys(RECIPES);

/**
 * The children a stagger applies to. A component marks them with
 * `data-motion-items`; otherwise the element's own children are used.
 */
function childItems(el) {
  const marked = $(el, '[data-motion-item]');
  return marked.length ? marked : Array.from(el.children);
}

/** Clear every "before" state a recipe may have applied. */
function revealAll(root) {
  const els = $(root, '[data-motion]');
  for (const el of els) {
    utils.remove?.(el);
    for (const node of [el, ...$(el, '*')]) {
      node.style.opacity = '';
      node.style.transform = '';
    }
  }
}

/**
 * Apply the declared motion under `root`.
 *
 * Under `prefers-reduced-motion: reduce` this applies no before-state and runs
 * no animation — the page is already in its final state, which is the point.
 */
export function initMotion(root = document) {
  if (prefersReduced()) return { reduced: true, applied: 0 };

  let applied = 0;
  const unknown = [];

  for (const el of $(root, '[data-motion]')) {
    const name = el.dataset.motion;
    const recipe = RECIPES[name];
    if (!recipe) { unknown.push(name); continue; }
    try {
      recipe(el);
      applied++;
    } catch (err) {
      // One bad recipe must never leave the deliverable half-invisible.
      console.error(`[motion] "${name}" failed; revealing content as-is.`, err);
      revealAll(el);
    }
  }

  if (unknown.length) {
    console.warn(`[motion] no recipe for: ${[...new Set(unknown)].join(', ')}`);
  }

  // Watchdog. If the scroll observer never fires for an element that is in the
  // viewport — a stale browser, a blocked API, a layout with no scroll range —
  // reveal it rather than leave a client staring at empty space.
  setTimeout(() => {
    for (const el of $(root, '[data-motion]')) {
      const box = el.getBoundingClientRect();
      const onScreen = box.top < innerHeight && box.bottom > 0;
      if (!onScreen) continue;
      for (const node of [el, ...$(el, '*')]) {
        if (getComputedStyle(node).opacity === '0') {
          node.style.opacity = '';
          node.style.transform = '';
        }
      }
    }
  }, 2500);

  return { reduced: false, applied };
}

/**
 * Keep the compact rail focused on the previous, current, and next sections.
 * Each update enters from the right, so the reader sees the context advance
 * left as they move through a long document.
 */
export function initRail(root = document) {
  const rail = root.querySelector('.rail');
  const source = rail?.querySelector('.rail__entries');
  if (!rail || !source || typeof IntersectionObserver !== 'function') return;
  let entries;
  try {
    entries = JSON.parse(source.textContent);
  } catch {
    return;
  }
  if (!Array.isArray(entries) || !entries.length) return;

  const slots = {
    previous: rail.querySelector('.rail__link--previous'),
    current: rail.querySelector('.rail__link--current'),
    next: rail.querySelector('.rail__link--next'),
  };
  const setSlot = (slot, entry, current = false) => {
    if (!slot) return;
    if (!entry) {
      slot.hidden = true;
      slot.removeAttribute('href');
      slot.removeAttribute('aria-current');
      slot.textContent = '';
      return;
    }
    slot.hidden = false;
    slot.href = `#${entry.id}`;
    slot.textContent = entry.label;
    if (current) slot.setAttribute('aria-current', 'location');
    else slot.removeAttribute('aria-current');
  };
  let activeIndex = 0;
  const update = (index, { animate: shouldAnimate = false } = {}) => {
    if (index === activeIndex && !shouldAnimate) return;
    activeIndex = index;
    setSlot(slots.previous, entries[index - 1]);
    setSlot(slots.current, entries[index], true);
    setSlot(slots.next, entries[index + 1]);
    if (shouldAnimate && !prefersReduced()) {
      const visible = Object.values(slots).filter((slot) => slot && !slot.hidden);
      animate(visible, { x: [24, 0], opacity: [0, 1], ease: 'outQuad', duration: 300 });
    }
  };

  const byId = new Map(entries.map((entry, index) => [entry.id, index]));
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      const index = byId.get(entry.target.id);
      if (index !== undefined) update(index, { animate: index !== activeIndex });
    }
  }, { rootMargin: '-45% 0px -50% 0px' });
  for (const id of byId.keys()) {
    const section = id && document.getElementById(id);
    if (section) observer.observe(section);
  }
}

/** Let readers inspect phases while retaining the map as the primary view. */
export function initExecutionMaps(root = document) {
  for (const map of $(root, '[data-component="execution_map"]')) {
    const scrubber = map.querySelector('.execution-map__scrubber input');
    const bars = $(map, '.execution-map__bar');
    const inspector = map.querySelector('.execution-map__inspector');
    const content = map.querySelector('.execution-map__inspector-content');
    const prompt = map.querySelector('.execution-map__prompt');
    const context = map.querySelector('.execution-map__context');
    let activeBar = null;

    const setPeriod = () => {
      const period = Number(scrubber?.value ?? 1);
      map.style.setProperty('--active-period', period);
      const active = bars.filter((bar) => period >= Number(bar.dataset.phaseStart) && period <= Number(bar.dataset.phaseEnd));
      for (const bar of bars) bar.classList.toggle('is-current', active.includes(bar));
      const activeNames = active.map((bar) => bar.querySelector('span')?.textContent).filter(Boolean);
      if (context) context.textContent = `Period ${String(period).padStart(2, '0')} · ${activeNames.length ? `${activeNames.join(' + ')} in focus.` : 'No phase is scheduled in this period.'}`;
    };
    const select = (bar) => {
      activeBar = bar;
      for (const item of bars) item.setAttribute('aria-expanded', String(item === bar));
      const source = bar.parentElement?.querySelector('.execution-map__source .timeline-detail');
      if (content && source) content.innerHTML = source.outerHTML;
      if (inspector) inspector.hidden = false;
      if (prompt) prompt.hidden = true;
    };
    scrubber?.addEventListener('input', setPeriod);
    for (const bar of bars) bar.addEventListener('click', () => select(bar));
    map.querySelector('.execution-map__collapse')?.addEventListener('click', () => {
      if (inspector) inspector.hidden = true;
      if (prompt) prompt.hidden = false;
      for (const bar of bars) bar.setAttribute('aria-expanded', 'false');
      activeBar?.focus();
    });
    setPeriod();
  }
}

if (typeof document !== 'undefined') {
  // Print with every figure at its final value, whether or not the reader ever
  // scrolled past it.
  addEventListener('beforeprint', finaliseMotion);
  matchMedia?.('print')?.addEventListener?.('change', (e) => { if (e.matches) finaliseMotion(); });

  const start = () => { initMotion(document); initRail(document); initExecutionMaps(document); };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
}

// Scope controls to their owning module so isolated and repeated views work.
for (const root of document.querySelectorAll('.reference-kickoff')) {
  const noteToggle = root.querySelector('.ref-note-toggle');
  const note = root.querySelector('.ref-design-note');
  noteToggle?.addEventListener('click', () => {
    const open = noteToggle.getAttribute('aria-expanded') !== 'true';
    noteToggle.setAttribute('aria-expanded', String(open));
    noteToggle.querySelector('span').textContent = open ? '−' : '+';
    note.hidden = !open;
    root.querySelector('.ref-module').classList.toggle('ref-notes-open', open);
  });
  for (const ring of root.querySelectorAll('.ref-ring[data-value]')) {
    ring.style.setProperty('--ref-ring', `${Math.min(Number(ring.dataset.value), 100) * 3.6}deg`);
  }
  const flowButtons = [...root.querySelectorAll('[data-flow]')];
  for (const button of flowButtons) button.addEventListener('click', () => {
    for (const candidate of flowButtons) candidate.setAttribute('aria-pressed', String(candidate === button));
    for (const node of root.querySelectorAll('.ref-arch-node')) {
      node.classList.toggle('ref-active', node.dataset.flows.split(' ').includes(button.dataset.flow));
    }
    const explanation = root.querySelector('.ref-flow-explanation');
    explanation.querySelector('b').textContent = button.textContent;
    explanation.querySelector('p').textContent = button.dataset.description;
  });
  const filters = [...root.querySelectorAll('[data-epic-filter]')];
  const entries = [...root.querySelectorAll('.ref-epic-entry')];
  const count = root.querySelector('.ref-epic-count');
  const allLabel = count?.textContent;
  for (const button of filters) button.addEventListener('click', () => {
    const key = button.dataset.epicFilter;
    for (const candidate of filters) candidate.setAttribute('aria-pressed', String(candidate === button));
    for (const entry of entries) entry.hidden = key !== 'All' && entry.dataset.release !== key;
    const visible = entries.filter((entry) => !entry.hidden).length;
    count.textContent = key === 'All' ? allLabel : `${visible} ${key === 'MVP' ? 'MVP epics' : 'later-release epic'}`;
  });
}
