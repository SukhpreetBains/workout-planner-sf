import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, typeset } from '../shared/primitives.mjs';

const view = (section) => `<div class="architecture-flow" data-motion="path-draw">
  <svg class="roadmap__path" viewBox="0 0 1000 50" role="img" aria-label="Logical flow across architecture components"><path d="M20 25 H980"></path></svg>
  <div class="architecture-flow__nodes">${section.phases.map((phase, index) => `<details class="architecture-node phase" data-motion-item${index === 0 ? ' open' : ''}><summary><span>${moduleIndex(index)} · ${typeset(phase.window)}</span><strong>${typeset(phase.name)}</strong></summary><ul>${phase.outcomes.map((outcome) => `<li>${typeset(outcome)}</li>`).join('')}</ul></details>`).join('')}</div>
</div>`;

const STANDARD_RENDERERS = { 'architecture': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m27">
<div class="module-shell">
<header class="module-head">
<div>
<div class="module-kicker">{{div-module-kicker-1}}</div>
<h2>{{div-h2-1}}</h2>
<p>{{div-p-1}}</p>
</div>
<button type="button" class="note-toggle" aria-expanded="false">{{reference-notes-summary-1}} <span>+</span></button>
</header>
<div class="module-visual added-visual">
<div class="added-intro">
<span class="eyebrow">{{added-intro-eyebrow-1}}</span>
<h3>{{added-intro-h3-1}}</h3>
<p>{{added-intro-p-1}}</p>
</div>
<div class="flow-controls" aria-label="Architecture flow">
<button type="button" data-flow="journey" data-description="{{flow-journey-description}}" aria-pressed="true">{{flow-controls-button-1}}</button>
<button type="button" data-flow="consent" data-description="{{flow-consent-description}}" aria-pressed="false">{{flow-controls-button-2}}</button>
<button type="button" data-flow="insight" data-description="{{flow-insight-description}}" aria-pressed="false">{{flow-controls-button-3}}</button>
</div>
<div class="arch-map" role="group" aria-label="Architecture components, from member to enterprise services">
<div class="arch-node" data-flows="journey consent insight">
<small>{{arch-node-small-1}}</small>
<h4>{{arch-node-h4-1}}</h4>
<p>{{arch-node-p-1}}</p>
</div>
<span class="arch-link" aria-hidden="true">{{arch-map-arch-link-1}}</span>
<div class="arch-node" data-flows="journey consent insight">
<small>{{arch-node-small-2}}</small>
<h4>{{arch-node-h4-2}}</h4>
<p>{{arch-node-p-2}}</p>
</div>
<span class="arch-link" aria-hidden="true">{{arch-map-arch-link-2}}</span>
<div class="arch-services">
<div class="arch-node" data-flows="consent">
<small>{{arch-node-small-3}}</small>
<h4>{{arch-node-h4-3}}</h4>
<p>{{arch-node-p-3}}</p>
</div>
<div class="arch-node" data-flows="journey">
<small>{{arch-node-small-4}}</small>
<h4>{{arch-node-h4-4}}</h4>
<p>{{arch-node-p-4}}</p>
</div>
<div class="arch-node" data-flows="insight">
<small>{{arch-node-small-5}}</small>
<h4>{{arch-node-h4-5}}</h4>
<p>{{arch-node-p-5}}</p>
</div>
</div>
</div>
<div class="flow-explanation" aria-live="polite">
<b>{{flow-explanation-b-1}}</b>
<p>{{flow-explanation-p-1}}</p>
</div>
<p class="added-foot">{{module-visual-added-foot-1}}</p>
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
</div>
</div>
</aside>
</div>
</div>`;

export const RENDERERS = Object.fromEntries(Object.entries(STANDARD_RENDERERS).map(([id, render]) => [id, (content, ctx) => content.layout === 'microsite' ? referenceLayout(MICROSITE_LAYOUT, content) : render(content, ctx)]));
