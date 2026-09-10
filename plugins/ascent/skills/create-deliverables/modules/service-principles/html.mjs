import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, typeset } from '../shared/primitives.mjs';

const view = (section) => `<div class="experience-journey" data-motion="stagger-up">${section.items.map((item, index) => `<article data-motion-item><span>${moduleIndex(index)}</span><h3>${typeset(item.title)}</h3><p>${typeset(item.detail)}</p></article>`).join('')}<strong class="experience-journey__target">Effort ↓ · Trust ↑</strong></div>`;

const STANDARD_RENDERERS = { 'service-principles': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m17">
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
<div class="cx-journey">
  <div class="cx-line">
</div>
  <div class="cx-point" style="--x:8%">
<i>
</i>
<b>{{cx-point-b-1}}</b>
<span>{{cx-point-span-1}}</span>
</div>
  <div class="cx-point" style="--x:31%">
<i>
</i>
<b>{{cx-point-b-2}}</b>
<span>{{cx-point-span-2}}</span>
</div>
  <div class="cx-point" style="--x:55%">
<i>
</i>
<b>{{cx-point-b-3}}</b>
<span>{{cx-point-span-3}}</span>
</div>
  <div class="cx-point" style="--x:79%">
<i>
</i>
<b>{{cx-point-b-4}}</b>
<span>{{cx-point-span-4}}</span>
</div>
  <div class="cx-sentiment">
<span>{{cx-sentiment-span-1}}</span>
<strong>{{cx-sentiment-strong-1}}</strong>
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
