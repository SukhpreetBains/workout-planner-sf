import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, typeset } from '../shared/primitives.mjs';

const view = (section) => `<div class="governance-ladder" data-motion="stagger-up">${section.phases.map((phase, index) => `<article data-motion-item><span>${moduleIndex(index)}</span><div><small>${typeset(phase.window)}</small><h3>${typeset(phase.name)}</h3><p>${phase.outcomes.map(typeset).join(' · ')}</p></div></article>`).join('')}<strong class="governance-ladder__escalate">Escalate blocked decisions through the ladder</strong></div>`;

const STANDARD_RENDERERS = { 'governance': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m13">
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
<div class="gov-stack">
  <div class="gov-tier exec">
<b>{{gov-tier-b-1}}</b>
<span>{{gov-tier-span-1}}</span>
<p>{{gov-tier-p-1}}</p>
<small>{{gov-tier-small-1}}</small>
</div>
  <div class="gov-tier program">
<b>{{gov-tier-b-2}}</b>
<span>{{gov-tier-span-2}}</span>
<p>{{gov-tier-p-2}}</p>
<small>{{gov-tier-small-2}}</small>
</div>
  <div class="gov-tier team">
<b>{{gov-tier-b-3}}</b>
<span>{{gov-tier-span-3}}</span>
<p>{{gov-tier-p-3}}</p>
<small>{{gov-tier-small-3}}</small>
</div>
  <div class="escalation-beam">
<i>
</i>
<span>{{escalation-beam-span-1}}</span>
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
