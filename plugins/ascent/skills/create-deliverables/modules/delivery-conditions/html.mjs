import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, typeset } from '../shared/primitives.mjs';

const view = (section) => `<div class="condition-board" data-motion="stagger-up">${section.findings.map((finding, index) => `<article data-motion-item><span>${moduleIndex(index)} · ${typeset(finding.theme)}</span><h3>${typeset(finding.evidence)}</h3><p>${typeset(finding.implication)}</p>${finding.severity ? `<div class="severity"><span>${typeset(finding.severity[0].toUpperCase() + finding.severity.slice(1))} severity</span></div>` : ''}</article>`).join('')}</div>`;

const STANDARD_RENDERERS = { 'conditions': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m19">
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
<div class="adri-grid">
  <article class="adri-card assumption">
<span>{{adri-card-span-1}}</span>
<h3>{{adri-card-h3-1}}</h3>
<p>{{adri-card-p-1}}</p>
</article>
  <article class="adri-card dependency">
<span>{{adri-card-span-2}}</span>
<h3>{{adri-card-h3-2}}</h3>
<p>{{adri-card-p-2}}</p>
</article>
  <article class="adri-card risk">
<span>{{adri-card-span-3}}</span>
<h3>{{adri-card-h3-3}}</h3>
<p>{{adri-card-p-3}}</p>
</article>
  <article class="adri-card issue">
<span>{{adri-card-span-4}}</span>
<h3>{{adri-card-h3-4}}</h3>
<p>{{adri-card-p-4}}</p>
</article>
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
