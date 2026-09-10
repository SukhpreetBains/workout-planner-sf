import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, typeset } from '../shared/primitives.mjs';

const view = (section) => `<div class="working-system" data-motion="stagger-up"><div class="working-system__core">One team</div>${section.items.map((item, index) => `<details class="working-system__norm norm-${index + 1}" data-motion-item><summary><span>${moduleIndex(index)}</span><strong>${typeset(item.title)}</strong></summary><p>${typeset(item.detail)}</p></details>`).join('')}</div>`;

const STANDARD_RENDERERS = { 'norms': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m16">
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
<div class="norm-system">
<div class="one-team">{{norm-system-one-team-1}}<br>{{norm-system-one-team-2}}</div>
  <article class="norm-card n1">
<b>{{norm-card-b-1}}</b>
<span>{{norm-card-span-1}}</span>
</article>
  <article class="norm-card n2">
<b>{{norm-card-b-2}}</b>
<span>{{norm-card-span-2}}</span>
</article>
  <article class="norm-card n3">
<b>{{norm-card-b-3}}</b>
<span>{{norm-card-span-3}}</span>
</article>
  <article class="norm-card n4">
<b>{{norm-card-b-4}}</b>
<span>{{norm-card-span-4}}</span>
</article>
  <article class="norm-card n5">
<b>{{norm-card-b-5}}</b>
<span>{{norm-card-span-5}}</span>
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
