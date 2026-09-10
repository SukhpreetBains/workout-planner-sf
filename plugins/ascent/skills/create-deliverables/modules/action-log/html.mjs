import { referenceLayout } from '../shared/reference-layout.mjs';
import { rawCell, rowCell, stateClass } from '../shared/primitives.mjs';

const view = (section) => `<div class="commitment-engine" data-motion="stagger-up">${section.rows.map((row) => `<article class="${stateClass(rawCell(row, 4))}" data-motion-item><span>${rowCell(row, 0)}</span><h3>${rowCell(row, 1)}</h3><p>Owner · ${rowCell(row, 2)} · Due ${rowCell(row, 3)}</p><strong>${rowCell(row, 4)}</strong><small>${rowCell(row, 5)}</small></article>`).join('')}</div>`;

const STANDARD_RENDERERS = { 'actions': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m22">
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
<div class="action-board">
  <article class="action-item">
<span>{{action-item-span-1}}</span>
<div>
<b>{{div-b-1}}</b>
<small>{{div-small-1}}</small>
</div>
<div class="action-progress">
<i style="--w:85%">
</i>
</div>
<em>{{action-item-em-1}}</em>
</article>
  <article class="action-item">
<span>{{action-item-span-2}}</span>
<div>
<b>{{div-b-2}}</b>
<small>{{div-small-2}}</small>
</div>
<div class="action-progress">
<i style="--w:60%">
</i>
</div>
<em>{{action-item-em-2}}</em>
</article>
  <article class="action-item">
<span>{{action-item-span-3}}</span>
<div>
<b>{{div-b-3}}</b>
<small>{{div-small-3}}</small>
</div>
<div class="action-progress">
<i style="--w:35%">
</i>
</div>
<em>{{action-item-em-3}}</em>
</article>
  <article class="action-item complete">
<span>{{action-item-span-4}}</span>
<div>
<b>{{div-b-4}}</b>
<small>{{div-small-4}}</small>
</div>
<div class="action-progress">
<i style="--w:100%">
</i>
</div>
<em>{{action-item-em-4}}</em>
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
