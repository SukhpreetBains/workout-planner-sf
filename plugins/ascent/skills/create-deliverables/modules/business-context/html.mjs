import { referenceLayout } from '../shared/reference-layout.mjs';
import { esc, moduleIndex, typeset } from '../shared/primitives.mjs';

const view = (section, ctx) => `<div class="context-flow" data-motion="stagger-up">
  ${section.findings.map((finding, index) => `<article class="context-flow__panel" data-motion-item>
    <div class="context-flow__label">${finding.icon ? `<img class="finding__icon" src="${esc(ctx.iconPath(finding.icon))}" alt="">` : ''}<p class="eyebrow">${moduleIndex(index)} · ${typeset(finding.theme)}</p></div>
    <h3>${typeset(finding.evidence)}</h3><p>${typeset(finding.implication)}</p>
    <span>${index < section.findings.length - 1 ? '→' : 'Value unlocked'}</span>
  </article>`).join('')}
</div>`;

const STANDARD_RENDERERS = { 'context': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m04">
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
<div class="context-flow">
  <article class="context-card pressure">
<span>{{context-card-span-1}}</span>
<h3>{{context-card-h3-1}}</h3>
<p>{{context-card-p-1}}</p>
<strong>{{context-card-strong-1}}</strong>
</article>
  <div class="context-arrow">{{context-flow-context-arrow-1}}</div>
  <article class="context-card catalyst">
<span>{{context-card-span-2}}</span>
<h3>{{context-card-h3-2}}</h3>
<p>{{context-card-p-2}}</p>
<strong>{{context-card-strong-2}}</strong>
</article>
  <div class="context-arrow">{{context-flow-context-arrow-2}}</div>
  <article class="context-card opportunity">
<span>{{context-card-span-3}}</span>
<h3>{{context-card-h3-3}}</h3>
<p>{{context-card-p-3}}</p>
<strong>{{context-card-strong-3}}</strong>
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
