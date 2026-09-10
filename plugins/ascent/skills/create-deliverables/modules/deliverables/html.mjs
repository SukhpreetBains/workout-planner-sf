import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, rowCell } from '../shared/primitives.mjs';

const view = (section) => `<div class="deliverable-grid" data-motion="stagger-up">${section.rows.map((row, index) => `<article data-motion-item><span>${moduleIndex(index)}</span><h3>${rowCell(row, 0)}</h3><p>${rowCell(row, 1)}</p><dl><div><dt>Owner</dt><dd>${rowCell(row, 2)}</dd></div><div><dt>Accept</dt><dd>${rowCell(row, 3)}</dd></div></dl></article>`).join('')}</div>`;

const STANDARD_RENDERERS = { 'deliverables': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m10">
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
<div class="deliverable-grid">
  <article class="deliverable-card">
<div class="d-icon">{{deliverable-card-d-icon-1}}</div>
<h3>{{deliverable-card-h3-1}}</h3>
<p>{{deliverable-card-p-1}}</p>
<div class="maturity">
<i style="--w:78%">
</i>
</div>
<small>{{deliverable-card-small-1}}</small>
</article>
  <article class="deliverable-card">
<div class="d-icon">{{deliverable-card-d-icon-2}}</div>
<h3>{{deliverable-card-h3-2}}</h3>
<p>{{deliverable-card-p-2}}</p>
<div class="maturity">
<i style="--w:58%">
</i>
</div>
<small>{{deliverable-card-small-2}}</small>
</article>
  <article class="deliverable-card">
<div class="d-icon">{{deliverable-card-d-icon-3}}</div>
<h3>{{deliverable-card-h3-3}}</h3>
<p>{{deliverable-card-p-3}}</p>
<div class="maturity">
<i style="--w:24%">
</i>
</div>
<small>{{deliverable-card-small-3}}</small>
</article>
  <article class="deliverable-card">
<div class="d-icon">{{deliverable-card-d-icon-4}}</div>
<h3>{{deliverable-card-h3-4}}</h3>
<p>{{deliverable-card-p-4}}</p>
<div class="maturity">
<i style="--w:10%">
</i>
</div>
<small>{{deliverable-card-small-4}}</small>
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
