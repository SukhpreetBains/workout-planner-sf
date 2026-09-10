import { referenceLayout } from '../shared/reference-layout.mjs';
import { initials, rawCell, rowCell } from '../shared/primitives.mjs';

const view = (section) => `<div class="stakeholder-map" data-motion="stagger-up"><span class="stakeholder-map__axis stakeholder-map__axis--x">Impact →</span><span class="stakeholder-map__axis stakeholder-map__axis--y">Influence →</span>${section.rows.map((row, index) => `<details class="stakeholder-point point-${index + 1}" data-motion-item><summary><b>${initials(rawCell(row, 0))}</b><span>${rowCell(row, 0)}</span></summary><p>${rowCell(row, 1)} · ${rowCell(row, 2)} influence</p><small>${rowCell(row, 3)} · Owner: ${rowCell(row, 4)}</small></details>`).join('')}<p class="stakeholder-map__label">Manage closely</p></div>`;

const STANDARD_RENDERERS = { 'stakeholders': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m12">
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
<div class="stake-map">
  <div class="axis y">
<span>{{axis-span-1}}</span>
<span>{{axis-span-2}}</span>
</div>
<div class="axis x">
<span>{{axis-span-3}}</span>
<span>{{axis-span-4}}</span>
</div>
  <button class="stake-dot priority" style="--x:79%;--y:18%">
<span>{{stake-dot-span-1}}</span>
<small>{{stake-dot-small-1}}</small>
</button>
  <button class="stake-dot priority" style="--x:68%;--y:28%">
<span>{{stake-dot-span-2}}</span>
<small>{{stake-dot-small-2}}</small>
</button>
  <button class="stake-dot" style="--x:60%;--y:43%">
<span>{{stake-dot-span-3}}</span>
<small>{{stake-dot-small-3}}</small>
</button>
  <button class="stake-dot" style="--x:85%;--y:52%">
<span>{{stake-dot-span-4}}</span>
<small>{{stake-dot-small-4}}</small>
</button>
  <button class="stake-dot" style="--x:44%;--y:62%">
<span>{{stake-dot-span-5}}</span>
<small>{{stake-dot-small-5}}</small>
</button>
  <button class="stake-dot" style="--x:72%;--y:76%">
<span>{{stake-dot-span-6}}</span>
<small>{{stake-dot-small-6}}</small>
</button>
  <div class="stake-legend">
<span>
<i class="priority-dot">
</i>{{stake-legend-span-1}}</span>
<span>
<i>
</i>{{stake-legend-span-2}}</span>
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
