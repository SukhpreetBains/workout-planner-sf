import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, rowCell } from '../shared/primitives.mjs';

const view = (section) => `<div class="cadence-week" data-motion="stagger-up">${section.rows.map((row, index) => `<article data-motion-item><span>${moduleIndex(index)}</span><small>${rowCell(row, 1)}</small><h3>${rowCell(row, 0)}</h3><p>${rowCell(row, 3)}</p><strong>${rowCell(row, 4)}</strong></article>`).join('')}</div>`;

const STANDARD_RENDERERS = { 'cadence': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m15">
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
<div class="cadence-week">
  <div class="day">
<b>{{day-b-1}}</b>
<div class="cadence-cell blue">
<span>{{cadence-cell-span-1}}</span>
<small>{{cadence-cell-small-1}}</small>
</div>
</div>
  <div class="day">
<b>{{day-b-2}}</b>
<div class="cadence-cell cyan">
<span>{{cadence-cell-span-2}}</span>
<small>{{cadence-cell-small-2}}</small>
</div>
</div>
  <div class="day">
<b>{{day-b-3}}</b>
<div class="cadence-cell blue">
<span>{{cadence-cell-span-3}}</span>
<small>{{cadence-cell-small-3}}</small>
</div>
</div>
  <div class="day">
<b>{{day-b-4}}</b>
<div class="cadence-cell lime">
<span>{{cadence-cell-span-4}}</span>
<small>{{cadence-cell-small-4}}</small>
</div>
</div>
  <div class="day">
<b>{{day-b-5}}</b>
<div class="cadence-cell blue">
<span>{{cadence-cell-span-5}}</span>
<small>{{cadence-cell-small-5}}</small>
</div>
</div>
</div>
<div class="cadence-note">{{module-visual-cadence-note-1}}</div>
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
