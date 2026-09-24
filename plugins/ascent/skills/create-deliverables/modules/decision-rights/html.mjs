import { referenceLayout } from '../shared/reference-layout.mjs';
import { rowCell } from '../shared/primitives.mjs';

const view = (section) => `<div class="decision-matrix" data-motion="stagger-up"><div class="decision-matrix__head"><span>Decision</span><span>Recommends</span><span>Approves</span><span>Consulted</span><span>Escalation</span></div>${section.rows.map((row) => `<div class="decision-matrix__row" data-motion-item>${row.cells.map((cell, index) => `<span${index === 0 ? ' class="decision-matrix__decision"' : ''}>${rowCell(row, index)}</span>`).join('')}</div>`).join('')}</div>`;

const STANDARD_RENDERERS = { 'decision-rights': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m14">
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
<div class="decision-matrix">
  <div class="dm-row head">
<b>{{dm-row-b-1}}</b>
<span>{{dm-row-span-1}}</span>
<span>{{dm-row-span-2}}</span>
<span>{{dm-row-span-3}}</span>
</div>
  <div class="dm-row">
<b>{{dm-row-b-2}}</b>
<span>{{dm-row-span-4}}</span>
<span class="hot">{{dm-row-hot-1}}</span>
<span>{{dm-row-span-5}}</span>
</div>
  <div class="dm-row">
<b>{{dm-row-b-3}}</b>
<span>{{dm-row-span-6}}</span>
<span class="hot">{{dm-row-hot-2}}</span>
<span>{{dm-row-span-7}}</span>
</div>
  <div class="dm-row">
<b>{{dm-row-b-4}}</b>
<span>{{dm-row-span-8}}</span>
<span class="hot">{{dm-row-hot-3}}</span>
<span>{{dm-row-span-9}}</span>
</div>
  <div class="dm-row">
<b>{{dm-row-b-5}}</b>
<span>{{dm-row-span-10}}</span>
<span class="hot">{{dm-row-hot-4}}</span>
<span>{{dm-row-span-11}}</span>
</div>
  <div class="dm-row">
<b>{{dm-row-b-6}}</b>
<span>{{dm-row-span-12}}</span>
<span class="hot">{{dm-row-hot-5}}</span>
<span>{{dm-row-span-13}}</span>
</div>
</div>
<div class="matrix-foot">{{module-visual-matrix-foot-1}}</div>
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
