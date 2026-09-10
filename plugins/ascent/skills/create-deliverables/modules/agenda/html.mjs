import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, typeset } from '../shared/primitives.mjs';

const view = (section) => `<div class="module-scene module-scene--agenda kickoff-agenda" data-motion="stagger-up">
  <div class="kickoff-agenda__rail" aria-hidden="true"></div>
  ${section.items.map((item, index) => `<details class="kickoff-agenda__stop" data-motion-item${index === 0 ? ' open' : ''}>
    <summary><span>${moduleIndex(index)}</span><strong>${typeset(item.title)}</strong></summary>
    <p>${typeset(item.detail)}</p>
  </details>`).join('')}
  <p class="kickoff-agenda__outcome">By the end of kickoff, the team can explain the destination, boundaries, operating model, and next action.</p>
</div>`;

const STANDARD_RENDERERS = { 'agenda': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m02">
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
<div class="agenda-rail">
  <div class="agenda-step">
<b>{{agenda-step-b-1}}</b>
<span>{{agenda-step-span-1}}</span>
<small>{{agenda-step-small-1}}</small>
</div>
  <div class="agenda-step">
<b>{{agenda-step-b-2}}</b>
<span>{{agenda-step-span-2}}</span>
<small>{{agenda-step-small-2}}</small>
</div>
  <div class="agenda-step">
<b>{{agenda-step-b-3}}</b>
<span>{{agenda-step-span-3}}</span>
<small>{{agenda-step-small-3}}</small>
</div>
  <div class="agenda-step">
<b>{{agenda-step-b-4}}</b>
<span>{{agenda-step-span-4}}</span>
<small>{{agenda-step-small-4}}</small>
</div>
  <div class="agenda-step">
<b>{{agenda-step-b-5}}</b>
<span>{{agenda-step-span-5}}</span>
<small>{{agenda-step-small-5}}</small>
</div>
</div>
<div class="objective-strip">
<strong>{{objective-strip-strong-1}}</strong> {{module-visual-objective-strip-1}}</div>
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
