import { referenceLayout } from '../shared/reference-layout.mjs';
import { moduleIndex, typeset, weekRange } from '../shared/primitives.mjs';

/**
 * Label and bar are laid out as separate grid columns, never overlapping —
 * the same separation `project-schedule` already uses (its bars never carry
 * text either). A fixed decorative header ("Start / Near term / Midpoint...")
 * and an independently-positioned bar cannot both be honest about timing at
 * once, so the header is now real week ticks spanning the same 1-to-`total`
 * scale the bars use, computed the same way from each phase's own
 * `phase.window` via `weekRange` (the "Week N-M" parser `project-schedule`
 * also uses) — not from the phase's index, which only ever matched one past
 * example's specific phase count and order by coincidence.
 */
function axisTicks(total, count = 4) {
  return Array.from({ length: count + 1 }, (_, i) => 1 + Math.round(((total - 1) * i) / count));
}

const view = (section) => {
  const ranges = section.phases.map((phase) => weekRange(phase.window, 1));
  const total = Math.max(1, ...ranges.map(({ start, span }) => start + span - 1));
  const axis = axisTicks(total).map((week) => `<span>Week ${week}</span>`).join('');
  const lanes = section.phases.map((phase, index) => {
    const { start, span } = ranges[index];
    const style = `--lane-start:${start - 1};--lane-span:${span};--lane-total:${total}`;
    return `<div class="roadmap-horizon__lane" data-motion-item>
      <div class="roadmap-horizon__label"><strong>${typeset(phase.name)}</strong><span>${typeset(phase.window)}</span><p>${phase.outcomes.map(typeset).join(' + ')}</p></div>
      <div class="roadmap-horizon__track" style="${style}"><i aria-hidden="true"></i></div>
    </div>`;
  }).join('');
  return `<div class="roadmap-horizon" data-motion="stagger-up">
  <div class="roadmap-horizon__axis" aria-hidden="true"><span class="roadmap-horizon__axis-spacer"></span><div class="roadmap-horizon__axis-ticks">${axis}</div></div>
  ${lanes}
</div>`;
};

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
