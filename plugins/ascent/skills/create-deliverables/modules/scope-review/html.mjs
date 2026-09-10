import { referenceLayout } from '../shared/reference-layout.mjs';
import { rowCell } from '../shared/primitives.mjs';

const view = (section) => `<div class="scope-boundary" data-motion="stagger-up">
  <div class="scope-boundary__side"><p class="eyebrow">In scope · first release</p>${section.rows.map((row) => `<span data-motion-item><strong>${rowCell(row, 0)}</strong>${rowCell(row, 1)}</span>`).join('')}</div>
  <div class="scope-boundary__control"><span>Change control</span></div>
  <div class="scope-boundary__side scope-boundary__side--deferred"><p class="eyebrow">Deferred or excluded</p>${section.rows.map((row) => `<span data-motion-item><strong>${rowCell(row, 0)}</strong><s>${rowCell(row, 2)}</s></span>`).join('')}</div>
</div>`;

const STANDARD_RENDERERS = { 'scope': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m06">
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
<div class="scope-board">
  <div class="scope-half in">
<div class="scope-label">{{scope-half-scope-label-1}}</div>
<div class="scope-items">
<span>{{scope-items-span-1}}</span>
<span>{{scope-items-span-2}}</span>
<span>{{scope-items-span-3}}</span>
<span>{{scope-items-span-4}}</span>
<span>{{scope-items-span-5}}</span>
<span>{{scope-items-span-6}}</span>
</div>
</div>
  <div class="scope-boundary">
<span>{{scope-boundary-span-1}}</span>
</div>
  <div class="scope-half out">
<div class="scope-label">{{scope-half-scope-label-2}}</div>
<div class="scope-items">
<span>{{scope-items-span-7}}</span>
<span>{{scope-items-span-8}}</span>
<span>{{scope-items-span-9}}</span>
<span>{{scope-items-span-10}}</span>
<span>{{scope-items-span-11}}</span>
</div>
</div>
</div>
<div class="scope-note">
<b>{{scope-note-b-1}}</b> {{module-visual-scope-note-1}}</div>
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
