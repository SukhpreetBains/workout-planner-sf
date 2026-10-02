import { referenceLayout } from '../shared/reference-layout.mjs';
import { typeset } from '../shared/primitives.mjs';

const view = (section) => `<div class="outcome-rings" data-motion="count-up">
  ${section.items.map((item, index) => {
    const numeric = typeof item.value === 'number';
    const amount = numeric ? Math.max(0, Math.min(100, Math.abs(item.value))) : 100;
    return `<article class="outcome-ring" data-motion-item>
      <div class="outcome-ring__chart"><svg viewBox="0 0 44 44" aria-hidden="true"><circle class="outcome-ring__track" cx="22" cy="22" r="18" pathLength="100"></circle><circle class="outcome-ring__value" cx="22" cy="22" r="18" pathLength="100" stroke-dasharray="${amount} ${100 - amount}"></circle></svg><p><span${numeric ? ` data-count-to="${item.value}"` : ''}>${typeset(item.value)}</span>${item.unit ? `<span>${typeset(item.unit)}</span>` : ''}</p></div>
      <h3>${typeset(item.label)}</h3><small>Signal · ${typeset(item.source)}</small>
    </article>`;
  }).join('')}
</div>`;

const STANDARD_RENDERERS = { 'outcomes': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m05">
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
<div class="outcome-grid">
  <article class="outcome-card">
<div class="ring" data-value="30">
<span>{{ring-span-1}}</span>
</div>
<h3>{{outcome-card-h3-1}}</h3>
<p>{{outcome-card-p-1}}</p>
<small>{{outcome-card-small-1}}</small>
</article>
  <article class="outcome-card">
<div class="ring" data-value="20">
<span>{{ring-span-2}}</span>
</div>
<h3>{{outcome-card-h3-2}}</h3>
<p>{{outcome-card-p-2}}</p>
<small>{{outcome-card-small-2}}</small>
</article>
  <article class="outcome-card">
<div class="ring" data-value="85">
<span>{{ring-span-3}}</span>
</div>
<h3>{{outcome-card-h3-3}}</h3>
<p>{{outcome-card-p-3}}</p>
<small>{{outcome-card-small-3}}</small>
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
