import { referenceLayout } from '../shared/reference-layout.mjs';
import { initials, moduleIndex, rawCell, rowCell } from '../shared/primitives.mjs';

const view = (section) => `<div class="team-constellation" data-motion="stagger-up">
  ${section.rows.map((row, index) => `<article class="person-card" data-motion-item>
    <span class="person-card__avatar" aria-hidden="true">${initials(rawCell(row, 0))}</span>
    <span class="module-index">${moduleIndex(index)}</span>
    <h3>${rowCell(row, 0)}</h3><p>${rowCell(row, 1)}</p><small>${rowCell(row, 2)}</small><strong>${rowCell(row, 3)}</strong>
  </article>`).join('')}
</div>`;

const STANDARD_RENDERERS = { 'roster': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m03">
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
<div class="team-grid">
  <div class="person-card client">
<div class="avatar">{{person-card-avatar-1}}</div>
<h3>{{person-card-h3-1}}</h3>
<p>{{person-card-p-1}}</p>
<small>{{person-card-small-1}}</small>
<div class="responsibility">{{person-card-responsibility-1}}</div>
</div>
  <div class="person-card client">
<div class="avatar">{{person-card-avatar-2}}</div>
<h3>{{person-card-h3-2}}</h3>
<p>{{person-card-p-2}}</p>
<small>{{person-card-small-2}}</small>
<div class="responsibility">{{person-card-responsibility-2}}</div>
</div>
  <div class="person-card client">
<div class="avatar">{{person-card-avatar-3}}</div>
<h3>{{person-card-h3-3}}</h3>
<p>{{person-card-p-3}}</p>
<small>{{person-card-small-3}}</small>
<div class="responsibility">{{person-card-responsibility-3}}</div>
</div>
  <div class="person-card partner">
<div class="avatar">{{person-card-avatar-4}}</div>
<h3>{{person-card-h3-4}}</h3>
<p>{{person-card-p-4}}</p>
<small>{{person-card-small-4}}</small>
<div class="responsibility">{{person-card-responsibility-4}}</div>
</div>
  <div class="person-card partner">
<div class="avatar">{{person-card-avatar-5}}</div>
<h3>{{person-card-h3-5}}</h3>
<p>{{person-card-p-5}}</p>
<small>{{person-card-small-5}}</small>
<div class="responsibility">{{person-card-responsibility-5}}</div>
</div>
  <div class="person-card partner">
<div class="avatar">{{person-card-avatar-6}}</div>
<h3>{{person-card-h3-6}}</h3>
<p>{{person-card-p-6}}</p>
<small>{{person-card-small-6}}</small>
<div class="responsibility">{{person-card-responsibility-6}}</div>
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
