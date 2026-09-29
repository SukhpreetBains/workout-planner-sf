import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, typeset } from '../shared/primitives.mjs';

const view = (section) => `<div class="mobilization-countdown" data-motion="stagger-up"><div class="mobilization-countdown__clock"><strong>48</strong><span>hours</span></div><ol>${section.items.map((item, index) => `<li data-motion-item data-citation-anchor="item-${index + 1}"><span>${moduleIndex(index)}</span><p>${typeset(item)}</p></li>`).join('')}</ol></div>`;

const STANDARD_RENDERERS = { 'next-steps': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m24">
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
<div class="launch-window">
  <div class="launch-count">
<span>{{launch-count-span-1}}</span>
<strong>{{launch-count-strong-1}}</strong>
<b>{{launch-count-b-1}}</b>
</div>
  <div class="launch-actions">
    <article data-citation-anchor="item-1">
<i>{{article-i-1}}</i>
<div>
<b>{{div-b-1}}</b>
<span>{{div-span-1}}</span>
</div>
<em>{{article-em-1}}</em>
</article>
    <article data-citation-anchor="item-2">
<i>{{article-i-2}}</i>
<div>
<b>{{div-b-2}}</b>
<span>{{div-span-2}}</span>
</div>
<em>{{article-em-2}}</em>
</article>
    <article data-citation-anchor="item-3">
<i>{{article-i-3}}</i>
<div>
<b>{{div-b-3}}</b>
<span>{{div-span-3}}</span>
</div>
<em>{{article-em-3}}</em>
</article>
    <article data-citation-anchor="item-4">
<i>{{article-i-4}}</i>
<div>
<b>{{div-b-4}}</b>
<span>{{div-span-4}}</span>
</div>
<em>{{article-em-4}}</em>
</article>
  </div>
</div>
</div>
        <aside class="design-note" hidden>
          <div>
<span>{{div-span-5}}</span>
<p>{{div-p-2}}</p>
</div>
          <div>
<span>{{div-span-6}}</span>
<p>{{div-p-3}}</p>
</div>
          <div class="source-signals">
<span>{{source-signals-span-1}}</span>
<div>
<span>{{div-span-7}}</span>
<span>{{div-span-8}}</span>
<span>{{div-span-9}}</span>
<span>{{div-span-10}}</span>
<span>{{div-span-11}}</span>
</div>
</div>
        </aside>
      </div>
    </div>`;

export const RENDERERS = Object.fromEntries(Object.entries(STANDARD_RENDERERS).map(([id, render]) => [id, (content, ctx) => content.layout === 'microsite' ? referenceLayout(MICROSITE_LAYOUT, content) : render(content, ctx)]));
