import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, rowCell } from '../shared/primitives.mjs';

const view = (section) => `<div class="epic-grid" data-motion="stagger-up">${section.rows.map((row, index) => `<details class="epic-card" data-motion-item><summary><span>${moduleIndex(index)} · ${rowCell(row, 1)}</span><h3>${rowCell(row, 0)}</h3><p>${rowCell(row, 2)}</p></summary><dl><div><dt>Owner</dt><dd>${rowCell(row, 3)}</dd></div><div><dt>Acceptance</dt><dd>${rowCell(row, 4)}</dd></div></dl></details>`).join('')}</div>`;

const STANDARD_RENDERERS = { 'epics': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m28">
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
<div class="epic-controls" aria-label="Filter epics">
<button type="button" data-epic-filter="All" aria-pressed="true">{{epic-controls-button-1}}</button>
<button type="button" data-epic-filter="MVP" aria-pressed="false">{{epic-controls-button-2}}</button>
<button type="button" data-epic-filter="Later" aria-pressed="false">{{epic-controls-button-3}}</button>
<span class="epic-count" aria-live="polite">{{epic-controls-epic-count-1}}</span>
</div>
<div class="epic-list">
<article class="epic-entry" data-release="MVP">
<div class="epic-id">{{epic-entry-epic-id-1}}<small>{{epic-id-small-1}}</small>
</div>
<div>
<h4>{{div-h4-1}}</h4>
<p>{{div-p-2}}</p>
<details>
<summary>{{details-summary-1}}</summary>
<p>
<b>{{p-b-1}}</b> {{details-p-1}}</p>
<p>
<b>{{p-b-2}}</b> {{details-p-2}}</p>
</details>
</div>
<div class="epic-owner">
<small>{{epic-owner-small-1}}</small>{{epic-entry-epic-owner-1}}</div>
</article>
<article class="epic-entry" data-release="MVP">
<div class="epic-id">{{epic-entry-epic-id-2}}<small>{{epic-id-small-2}}</small>
</div>
<div>
<h4>{{div-h4-2}}</h4>
<p>{{div-p-3}}</p>
<details>
<summary>{{details-summary-2}}</summary>
<p>
<b>{{p-b-3}}</b> {{details-p-3}}</p>
<p>
<b>{{p-b-4}}</b> {{details-p-4}}</p>
</details>
</div>
<div class="epic-owner">
<small>{{epic-owner-small-2}}</small>{{epic-entry-epic-owner-2}}</div>
</article>
<article class="epic-entry" data-release="MVP">
<div class="epic-id">{{epic-entry-epic-id-3}}<small>{{epic-id-small-3}}</small>
</div>
<div>
<h4>{{div-h4-3}}</h4>
<p>{{div-p-4}}</p>
<details>
<summary>{{details-summary-3}}</summary>
<p>
<b>{{p-b-5}}</b> {{details-p-5}}</p>
<p>
<b>{{p-b-6}}</b> {{details-p-6}}</p>
</details>
</div>
<div class="epic-owner">
<small>{{epic-owner-small-3}}</small>{{epic-entry-epic-owner-3}}</div>
</article>
<article class="epic-entry" data-release="MVP">
<div class="epic-id">{{epic-entry-epic-id-4}}<small>{{epic-id-small-4}}</small>
</div>
<div>
<h4>{{div-h4-4}}</h4>
<p>{{div-p-5}}</p>
<details>
<summary>{{details-summary-4}}</summary>
<p>
<b>{{p-b-7}}</b> {{details-p-7}}</p>
<p>
<b>{{p-b-8}}</b> {{details-p-8}}</p>
</details>
</div>
<div class="epic-owner">
<small>{{epic-owner-small-4}}</small>{{epic-entry-epic-owner-4}}</div>
</article>
<article class="epic-entry" data-release="Later">
<div class="epic-id">{{epic-entry-epic-id-5}}<small>{{epic-id-small-5}}</small>
</div>
<div>
<h4>{{div-h4-5}}</h4>
<p>{{div-p-6}}</p>
<details>
<summary>{{details-summary-5}}</summary>
<p>
<b>{{p-b-9}}</b> {{details-p-9}}</p>
<p>
<b>{{p-b-10}}</b> {{details-p-10}}</p>
</details>
</div>
<div class="epic-owner">
<small>{{epic-owner-small-5}}</small>{{epic-entry-epic-owner-5}}</div>
</article>
</div>
<p class="added-foot">{{module-visual-added-foot-1}}</p>
</div>
<aside class="design-note" hidden>
<div>
<span>{{div-span-1}}</span>
<p>{{div-p-7}}</p>
</div>
<div>
<span>{{div-span-2}}</span>
<p>{{div-p-8}}</p>
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
