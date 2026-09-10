import { referenceLayout } from '../shared/reference-layout.mjs';
import { rawCell, rowCell, stateClass } from '../shared/primitives.mjs';

const view = (section) => `<div class="management-queue" data-motion="stagger-up">${section.rows.map((row) => `<article class="${stateClass(rawCell(row, 5))}" data-motion-item><span>${rowCell(row, 0)}</span><strong>${rowCell(row, 1)}</strong><h3>${rowCell(row, 2)}</h3><p>${rowCell(row, 3)} · ${rowCell(row, 4)}</p><b>${rowCell(row, 5)}</b></article>`).join('')}</div>`;

const STANDARD_RENDERERS = { 'raid-log': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m20">
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
<div class="raid-table">
  <div class="raid-row head">
<span>{{raid-row-span-1}}</span>
<span>{{raid-row-span-2}}</span>
<span>{{raid-row-span-3}}</span>
<span>{{raid-row-span-4}}</span>
<span>{{raid-row-span-5}}</span>
<span>{{raid-row-span-6}}</span>
</div>
  <div class="raid-row raid-card high">
<span>{{raid-row-span-7}}</span>
<span>{{raid-row-span-8}}</span>
<span>{{raid-row-span-9}}</span>
<span>{{raid-row-span-10}}</span>
<span>{{raid-row-span-11}}</span>
<span class="pill red">{{raid-row-pill-1}}</span>
</div>
  <div class="raid-row raid-card med">
<span>{{raid-row-span-12}}</span>
<span>{{raid-row-span-13}}</span>
<span>{{raid-row-span-14}}</span>
<span>{{raid-row-span-15}}</span>
<span>{{raid-row-span-16}}</span>
<span class="pill blue">{{raid-row-pill-2}}</span>
</div>
  <div class="raid-row raid-card med">
<span>{{raid-row-span-17}}</span>
<span>{{raid-row-span-18}}</span>
<span>{{raid-row-span-19}}</span>
<span>{{raid-row-span-20}}</span>
<span>{{raid-row-span-21}}</span>
<span class="pill amber">{{raid-row-pill-3}}</span>
</div>
  <div class="raid-row raid-card low">
<span>{{raid-row-span-22}}</span>
<span>{{raid-row-span-23}}</span>
<span>{{raid-row-span-24}}</span>
<span>{{raid-row-span-25}}</span>
<span>{{raid-row-span-26}}</span>
<span class="pill green">{{raid-row-pill-4}}</span>
</div>
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
