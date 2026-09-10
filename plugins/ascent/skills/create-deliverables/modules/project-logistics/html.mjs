import { referenceLayout } from '../shared/reference-layout.mjs';
import { rawCell, rowCell, stateClass } from '../shared/primitives.mjs';

const view = (section) => `<div class="readiness-cockpit" data-motion="stagger-up">${section.rows.map((row) => `<article class="${stateClass(rawCell(row, 4))}" data-motion-item><header><h3>${rowCell(row, 0)}</h3><strong>${rowCell(row, 4)}</strong></header><p>${rowCell(row, 1)}</p><small>${rowCell(row, 2)} · Needed ${rowCell(row, 3)}</small></article>`).join('')}</div>`;

const STANDARD_RENDERERS = { 'logistics': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m18">
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
<div class="readiness-grid">
  <article class="tool-node ready">
<i>
</i>
<b>{{tool-node-b-1}}</b>
<span>{{tool-node-span-1}}</span>
<small>{{tool-node-small-1}}</small>
</article>
  <article class="tool-node ready">
<i>
</i>
<b>{{tool-node-b-2}}</b>
<span>{{tool-node-span-2}}</span>
<small>{{tool-node-small-2}}</small>
</article>
  <article class="tool-node ready">
<i>
</i>
<b>{{tool-node-b-3}}</b>
<span>{{tool-node-span-3}}</span>
<small>{{tool-node-small-3}}</small>
</article>
  <article class="tool-node watch">
<i>
</i>
<b>{{tool-node-b-4}}</b>
<span>{{tool-node-span-4}}</span>
<small>{{tool-node-small-4}}</small>
</article>
  <article class="tool-node blocked">
<i>
</i>
<b>{{tool-node-b-5}}</b>
<span>{{tool-node-span-5}}</span>
<small>{{tool-node-small-5}}</small>
</article>
  <article class="tool-node ready">
<i>
</i>
<b>{{tool-node-b-6}}</b>
<span>{{tool-node-span-6}}</span>
<small>{{tool-node-small-6}}</small>
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
