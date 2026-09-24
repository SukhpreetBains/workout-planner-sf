import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, typeset } from '../shared/primitives.mjs';

const view = (section) => `<div class="delivery-spine" data-motion="stagger-up">${section.phases.map((phase, index) => `<article data-motion-item><span>${moduleIndex(index)}</span><strong>${typeset(phase.name)}</strong><small>${typeset(phase.window)}</small><p>${phase.outcomes.map(typeset).join(' + ')}</p></article>`).join('')}</div>`;

const STANDARD_RENDERERS = { 'approach': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m07">
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
<div class="phase-spine">
  <div class="phase-card"><b>{{phase-card-b-1}}</b><span>{{phase-card-span-1}}</span><small>{{phase-card-small-1}}</small></div>
  <div class="phase-card"><b>{{phase-card-b-2}}</b><span>{{phase-card-span-2}}</span><small>{{phase-card-small-2}}</small></div>
  <div class="phase-card"><b>{{phase-card-b-3}}</b><span>{{phase-card-span-3}}</span><small>{{phase-card-small-3}}</small></div>
  <div class="phase-card"><b>{{phase-card-b-4}}</b><span>{{phase-card-span-4}}</span><small>{{phase-card-small-4}}</small></div>
  <div class="phase-card"><b>{{phase-card-b-5}}</b><span>{{phase-card-span-5}}</span><small>{{phase-card-small-5}}</small></div>
</div>
<div class="phase-gates"><span>{{phase-gates-span-1}}</span><span>{{phase-gates-span-2}}</span><span>{{phase-gates-span-3}}</span></div>
</div>
        <aside class="design-note" hidden>
          <div><span>{{div-span-1}}</span><p>{{div-p-2}}</p></div>
          <div><span>{{div-span-2}}</span><p>{{div-p-3}}</p></div>
          <div class="source-signals">
<span>{{source-signals-span-1}}</span>
<div><span>{{div-span-3}}</span><span>{{div-span-4}}</span><span>{{div-span-5}}</span><span>{{div-span-6}}</span><span>{{div-span-7}}</span></div>
</div>
        </aside>
      </div>
    </div>`;

export const RENDERERS = Object.fromEntries(Object.entries(STANDARD_RENDERERS).map(([id, render]) => [id, (content, ctx) => content.layout === 'microsite' ? referenceLayout(MICROSITE_LAYOUT, content) : render(content, ctx)]));
