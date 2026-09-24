import { referenceLayout } from '../shared/reference-layout.mjs';
import { rowCell } from '../shared/primitives.mjs';

const view = (section) => `<div class="org-chart" data-motion="stagger-up">
  <div class="org-chart__sponsor" data-motion-item><strong>${rowCell(section.rows[0], 1)}</strong><small>${rowCell(section.rows[0], 2)}</small></div>
  <div class="org-chart__leadership">${section.rows.slice(1, 4).map((row) => `<article data-motion-item><strong>${rowCell(row, 1)}</strong><small>${rowCell(row, 2)}</small></article>`).join('')}</div>
  <div class="org-chart__workstreams">${section.rows.slice(4).map((row) => `<article data-motion-item><strong>${rowCell(row, 0)}</strong><span>${rowCell(row, 1)}</span><small>${rowCell(row, 2)}</small></article>`).join('')}</div>
</div>`;

const STANDARD_RENDERERS = { 'team-structure': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m11">
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
<div class="org-tree">
  <div class="org-node top">
<b>{{org-node-b-1}}</b>
<span>{{org-node-span-1}}</span>
</div>
  <div class="org-connector vertical">
</div>
  <div class="org-row">
<div class="org-node">
<b>{{org-node-b-2}}</b>
<span>{{org-node-span-2}}</span>
</div>
<div class="org-node">
<b>{{org-node-b-3}}</b>
<span>{{org-node-span-3}}</span>
</div>
<div class="org-node">
<b>{{org-node-b-4}}</b>
<span>{{org-node-span-4}}</span>
</div>
</div>
  <div class="org-connector horizontal">
</div>
  <div class="org-row workstreams">
<div class="org-node small">
<b>{{org-node-b-5}}</b>
<span>{{org-node-span-5}}</span>
</div>
<div class="org-node small">
<b>{{org-node-b-6}}</b>
<span>{{org-node-span-6}}</span>
</div>
<div class="org-node small">
<b>{{org-node-b-7}}</b>
<span>{{org-node-span-7}}</span>
</div>
<div class="org-node small">
<b>{{org-node-b-8}}</b>
<span>{{org-node-span-8}}</span>
</div>
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
