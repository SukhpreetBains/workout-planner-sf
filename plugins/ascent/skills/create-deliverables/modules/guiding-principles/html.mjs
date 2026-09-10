import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, typeset } from '../shared/primitives.mjs';

const view = (section) => `<div class="principle-deck" data-motion="stagger-up">${section.items.map((item, index) => `<details data-motion-item${index === 0 ? ' open' : ''}><summary><span>${moduleIndex(index)}</span><strong>${typeset(item.title)}</strong><b aria-hidden="true">+</b></summary><p>${typeset(item.detail)}</p></details>`).join('')}</div>`;

const STANDARD_RENDERERS = { 'principles': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m26">
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
<div class="principle-ledger">
<details class="guide-item">
<summary>
<span class="guide-number">{{summary-guide-number-1}}</span>
<span>
<b>{{span-b-1}}</b>
<small>{{span-small-1}}</small>
</span>
</summary>
<p>{{guide-item-p-1}}</p>
</details>
<details class="guide-item">
<summary>
<span class="guide-number">{{summary-guide-number-2}}</span>
<span>
<b>{{span-b-2}}</b>
<small>{{span-small-2}}</small>
</span>
</summary>
<p>{{guide-item-p-2}}</p>
</details>
<details class="guide-item">
<summary>
<span class="guide-number">{{summary-guide-number-3}}</span>
<span>
<b>{{span-b-3}}</b>
<small>{{span-small-3}}</small>
</span>
</summary>
<p>{{guide-item-p-3}}</p>
</details>
<details class="guide-item">
<summary>
<span class="guide-number">{{summary-guide-number-4}}</span>
<span>
<b>{{span-b-4}}</b>
<small>{{span-small-4}}</small>
</span>
</summary>
<p>{{guide-item-p-4}}</p>
</details>
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
