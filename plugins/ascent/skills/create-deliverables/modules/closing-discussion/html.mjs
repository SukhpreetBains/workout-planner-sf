import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, typeset } from '../shared/primitives.mjs';

const view = (section) => `<div class="closing-commitments" data-motion="stagger-up"><div class="closing-commitments__signal"><span>Ready to start</span><strong>Outcomes · Scope · Team · Rhythm</strong></div><ol>${section.items.map((item, index) => `<li data-motion-item><span>${moduleIndex(index)}</span><p>${typeset(item)}</p></li>`).join('')}</ol><p class="closing-commitments__question">What would prevent us from saying we are ready to start?</p></div>`;

const STANDARD_RENDERERS = { 'closing': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m25">
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
<div class="closing-grid">
  <div class="closing-orbit">
<div class="co-ring">
</div>
<div class="co-core">{{closing-orbit-co-core-1}}<br>{{closing-orbit-co-core-2}}<br>{{closing-orbit-co-core-3}}</div>
<span class="co a">{{closing-orbit-co-1}}</span>
<span class="co b">{{closing-orbit-co-2}}</span>
<span class="co c">{{closing-orbit-co-3}}</span>
<span class="co d">{{closing-orbit-co-4}}</span>
</div>
  <div class="closing-copy">
<div class="eyebrow">{{closing-copy-eyebrow-1}}</div>
<h3>{{closing-copy-h3-1}}</h3>
<ul>
<li>{{ul-li-1}}</li>
<li>{{ul-li-2}}</li>
<li>{{ul-li-3}}</li>
<li>{{ul-li-4}}</li>
</ul>
<div class="discussion-prompt">{{closing-copy-discussion-prompt-1}}</div>
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
</div>
</div>
        </aside>
      </div>
    </div>`;

export const RENDERERS = Object.fromEntries(Object.entries(STANDARD_RENDERERS).map(([id, render]) => [id, (content, ctx) => content.layout === 'microsite' ? referenceLayout(MICROSITE_LAYOUT, content) : render(content, ctx)]));
