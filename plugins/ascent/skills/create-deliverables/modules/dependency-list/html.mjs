import { referenceLayout } from '../shared/reference-layout.mjs';
import { rowCell } from '../shared/primitives.mjs';

const view = (section) => `<div class="dependency-network" data-motion="stagger-up">${section.rows.map((row, index) => `<article data-motion-item><span>${rowCell(row, 0)}</span><h3>${rowCell(row, 1)}</h3><p>${rowCell(row, 2)} · Required ${rowCell(row, 3)}</p><strong>${rowCell(row, 4)}</strong><small>Fallback: ${rowCell(row, 5)}</small>${index < section.rows.length - 1 ? '<i aria-hidden="true">→</i>' : ''}</article>`).join('')}</div>`;

const STANDARD_RENDERERS = { 'dependencies': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m21">
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
<div class="dep-list">
  <div class="dep-list-head"><span>Dependency</span><span>Owner</span><span>Required by</span></div>
  <ol>
<li><span class="dep-order">01</span><b>{{dep-node-b-1}}</b><span>{{dep-node-span-1}}</span><time>{{dep-node-small-1}}</time></li>
<li><span class="dep-order">02</span><b>{{dep-node-b-2}}</b><span>{{dep-node-span-2}}</span><time>{{dep-node-small-2}}</time></li>
<li><span class="dep-order">03</span><b>{{dep-node-b-3}}</b><span>{{dep-node-span-3}}</span><time>{{dep-node-small-3}}</time></li>
<li><span class="dep-order">04</span><b>{{dep-node-b-4}}</b><span>{{dep-node-span-4}}</span><time>{{dep-node-small-4}}</time></li>
<li><span class="dep-order">05</span><b>{{dep-node-b-5}}</b><span>{{dep-node-span-5}}</span><time>{{dep-node-small-5}}</time></li>
  </ol>
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
