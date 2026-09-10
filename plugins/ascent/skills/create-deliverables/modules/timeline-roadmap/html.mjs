import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, typeset } from '../shared/primitives.mjs';

const view = (section) => `<div class="roadmap-horizon" data-motion="stagger-up">
  <div class="roadmap-horizon__months" aria-hidden="true"><span>Start</span><span>Near term</span><span>Midpoint</span><span>Later</span><span>Transition</span></div>
  ${section.phases.map((phase, index) => `<div class="roadmap-horizon__lane lane-${index + 1}" data-motion-item><strong>${typeset(phase.name)}</strong><span>${typeset(phase.window)}</span><p>${phase.outcomes.map(typeset).join(' + ')}</p><i aria-hidden="true"></i></div>`).join('')}
  <div class="roadmap-horizon__milestones"><span>◆ Alignment</span><span>◆ Readiness</span><span>◆ Handoff</span></div>
</div>`;

const STANDARD_RENDERERS = { 'timeline': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m08">
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
<div class="roadmap">
  <div class="roadmap-axis">
<span>{{roadmap-axis-span-1}}</span>
<span>{{roadmap-axis-span-2}}</span>
<span>{{roadmap-axis-span-3}}</span>
<span>{{roadmap-axis-span-4}}</span>
<span>{{roadmap-axis-span-5}}</span>
</div>
  <div class="roadmap-row">
<label>{{roadmap-row-label-1}}</label>
<div class="roadmap-phase p1" style="--start:0;--span:18">{{roadmap-row-roadmap-phase-1}}</div>
</div>
  <div class="roadmap-row">
<label>{{roadmap-row-label-2}}</label>
<div class="roadmap-phase p2" style="--start:12;--span:28">{{roadmap-row-roadmap-phase-2}}</div>
</div>
  <div class="roadmap-row">
<label>{{roadmap-row-label-3}}</label>
<div class="roadmap-phase p3" style="--start:30;--span:42">{{roadmap-row-roadmap-phase-3}}</div>
</div>
  <div class="roadmap-row">
<label>{{roadmap-row-label-4}}</label>
<div class="roadmap-phase p4" style="--start:64;--span:22">{{roadmap-row-roadmap-phase-4}}</div>
</div>
  <div class="roadmap-row">
<label>{{roadmap-row-label-5}}</label>
<div class="roadmap-phase p5" style="--start:82;--span:18">{{roadmap-row-roadmap-phase-5}}</div>
</div>
  <div class="milestone m1" style="left:40%">
<i>
</i>
<span>{{milestone-span-1}}</span>
</div>
<div class="milestone m2" style="left:72%">
<i>
</i>
<span>{{milestone-span-2}}</span>
</div>
<div class="milestone m3" style="left:92%">
<i>
</i>
<span>{{milestone-span-3}}</span>
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
