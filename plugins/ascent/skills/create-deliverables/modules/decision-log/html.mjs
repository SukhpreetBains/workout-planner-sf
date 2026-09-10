import { referenceLayout } from '../shared/reference-layout.mjs';
import { rawCell, rowCell, stateClass } from '../shared/primitives.mjs';

const view = (section) => `<div class="decision-timeline" data-motion="stagger-up">${section.rows.map((row) => `<article class="${stateClass(rawCell(row, 1))}" data-motion-item><span>${rowCell(row, 0)}</span><strong>${rowCell(row, 1)}</strong><h3>${rowCell(row, 2)}</h3><p>${rowCell(row, 4)}</p><small>${rowCell(row, 3)} · Follow-up: ${rowCell(row, 5)}</small></article>`).join('')}</div>`;

const STANDARD_RENDERERS = { 'decisions': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m23">
      <div class="module-shell">
        <header class="module-head">
          <div>
<div class="module-kicker">{{div-module-kicker-1}}</div>
<h2>{{div-h2-1}}</h2>
<p>{{div-p-1}}</p>
</div>
        <button type="button" class="note-toggle" aria-expanded="false">{{reference-notes-summary-1}} <span>+</span></button>
</header>
        <div class="module-visual">
<div class="decision-rail">
  <article class="decision-item">
<time>{{decision-item-time-1}}</time>
<div class="decision-stamp">{{decision-item-decision-stamp-1}}</div>
<h3>{{decision-item-h3-1}}</h3>
<p>{{decision-item-p-1}}</p>
<small>{{decision-item-small-1}}</small>
</article>
  <article class="decision-item">
<time>{{decision-item-time-2}}</time>
<div class="decision-stamp">{{decision-item-decision-stamp-2}}</div>
<h3>{{decision-item-h3-2}}</h3>
<p>{{decision-item-p-2}}</p>
<small>{{decision-item-small-2}}</small>
</article>
  <article class="decision-item pending">
<time>{{decision-item-time-3}}</time>
<div class="decision-stamp">{{decision-item-decision-stamp-3}}</div>
<h3>{{decision-item-h3-3}}</h3>
<p>{{decision-item-p-3}}</p>
<small>{{decision-item-small-3}}</small>
</article>
</div>
</div>
        <aside class="design-note" hidden>
          <div>
<span>{{div-span-1}}</span>
<p>{{div-p-2}}</p>
</div>
          <div>
<span>{{div-span-2}}</span>
<p>{{div-p-3}}</p>
</div>
          <div class="source-signals">
<span>{{source-signals-span-1}}</span>
<div>
<span>{{div-span-3}}</span>
<span>{{div-span-4}}</span>
<span>{{div-span-5}}</span>
<span>{{div-span-6}}</span>
<span>{{div-span-7}}</span>
</div>
</div>
        </aside>
      </div>
    </div>`;

export const RENDERERS = Object.fromEntries(Object.entries(STANDARD_RENDERERS).map(([id, render]) => [id, (content, ctx) => content.layout === 'microsite' ? referenceLayout(MICROSITE_LAYOUT, content) : render(content, ctx)]));
