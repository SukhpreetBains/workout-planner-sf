import { referenceLayout } from '../shared/reference-layout.mjs';
import { renderCover } from '../shared/primitives.mjs';

const cover = (meta, ctx) => renderCover(meta, ctx);

const STANDARD_RENDERERS = { cover };


const MICROSITE_LAYOUT = `<div class="module cover" data-reference-id="m01">
      <div class="module-shell">
        <header class="module-head">
          <div>
<div class="module-kicker">{{div-module-kicker-1}}</div>
<p class="module-title">{{div-h2-1}}</p>
<p>{{div-p-1}}</p>
</div>
        <button type="button" class="note-toggle" aria-expanded="false">{{reference-notes-summary-1}} <span>+</span></button>
</header>
        <div class="module-visual">
<div class="hero-stage">
  <div class="hero-copy">
    <div class="eyebrow cyan">{{hero-copy-eyebrow-1}}</div>
    <h1 class="kinetic-title">{{hero-copy-kinetic-title-1}}<br>
<span>{{kinetic-title-span-1}}</span>
</h1>
    <p class="hero-sub">{{hero-copy-hero-sub-1}}</p>
    <div class="hero-meta">
<span>{{hero-meta-span-1}}</span>
<span>{{hero-meta-span-2}}</span>
<span class="classification">{{hero-meta-span-3}}</span>
</div>
  </div>
  <div class="pulse-orbit" aria-hidden="true">
<div class="orbit-ring r1">
</div>
<div class="orbit-ring r2">
</div>
<div class="project-pulse">
</div>
<div class="orbit-label l1">{{pulse-orbit-orbit-label-1}}</div>
<div class="orbit-label l2">{{pulse-orbit-orbit-label-2}}</div>
<div class="orbit-label l3">{{pulse-orbit-orbit-label-3}}</div>
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
