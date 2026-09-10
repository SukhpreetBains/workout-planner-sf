import { referenceLayout } from '../shared/reference-layout.mjs';
import { initials, rawCell, rowCell, weekRange } from '../shared/primitives.mjs';

const view = (section) => `<div class="schedule-gantt" data-motion="stagger-up">
  <div class="schedule-gantt__head"><span>Workstream</span>${Array.from({ length: 16 }, (_, i) => `<span>W${i + 1}</span>`).join('')}<span>Owner</span></div>
  ${section.rows.map((row, index) => { const range = weekRange(row.cells[1], index * 2 + 1); return `<div class="schedule-gantt__row" data-motion-item><div class="schedule-gantt__name"><strong>${rowCell(row, 0)}</strong><small>${rowCell(row, 2)}</small></div><div class="schedule-gantt__track"><span style="--gantt-start:${range.start};--gantt-span:${range.span}" aria-label="${rowCell(row, 2)}"></span></div><b>${initials(rawCell(row, 3))}</b></div>`; }).join('')}
  <div class="schedule-gantt__milestones"><span>◆ Design gate</span><span>◆ Acceptance ready</span><span>◆ Launch</span></div>
</div>`;

const STANDARD_RENDERERS = { 'schedule': view };

const MICROSITE_LAYOUT = `<div class="module" data-reference-id="m09">
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
<div class="gantt">
  <div class="gantt-head">
<span>{{gantt-head-span-1}}</span>
<div class="weeks">
<i>{{weeks-i-1}}</i>
<i>{{weeks-i-2}}</i>
<i>{{weeks-i-3}}</i>
<i>{{weeks-i-4}}</i>
<i>{{weeks-i-5}}</i>
<i>{{weeks-i-6}}</i>
<i>{{weeks-i-7}}</i>
<i>{{weeks-i-8}}</i>
<i>{{weeks-i-9}}</i>
<i>{{weeks-i-10}}</i>
<i>{{weeks-i-11}}</i>
<i>{{weeks-i-12}}</i>
<i>{{weeks-i-13}}</i>
<i>{{weeks-i-14}}</i>
<i>{{weeks-i-15}}</i>
<i>{{weeks-i-16}}</i>
</div>
</div>
  <div class="gantt-row">
<label>{{gantt-row-label-1}}</label>
<div class="gantt-track">
<span class="gantt-bar" style="--s:0;--w:18">
</span>
</div>
<b>{{gantt-row-b-1}}</b>
</div>
  <div class="gantt-row">
<label>{{gantt-row-label-2}}</label>
<div class="gantt-track">
<span class="gantt-bar" style="--s:10;--w:28">
</span>
</div>
<b>{{gantt-row-b-2}}</b>
</div>
  <div class="gantt-row">
<label>{{gantt-row-label-3}}</label>
<div class="gantt-track">
<span class="gantt-bar" style="--s:28;--w:38">
</span>
</div>
<b>{{gantt-row-b-3}}</b>
</div>
  <div class="gantt-row">
<label>{{gantt-row-label-4}}</label>
<div class="gantt-track">
<span class="gantt-bar risk" style="--s:34;--w:34">
</span>
</div>
<b>{{gantt-row-b-4}}</b>
</div>
  <div class="gantt-row">
<label>{{gantt-row-label-5}}</label>
<div class="gantt-track">
<span class="gantt-bar" style="--s:65;--w:22">
</span>
</div>
<b>{{gantt-row-b-5}}</b>
</div>
  <div class="gantt-row">
<label>{{gantt-row-label-6}}</label>
<div class="gantt-track">
<span class="gantt-bar" style="--s:86;--w:14">
</span>
</div>
<b>{{gantt-row-b-6}}</b>
</div>
  <div class="gantt-pin" style="left:41%">
<span>{{gantt-pin-span-1}}</span>
<small>{{gantt-pin-small-1}}</small>
</div>
<div class="gantt-pin" style="left:72%">
<span>{{gantt-pin-span-2}}</span>
<small>{{gantt-pin-small-2}}</small>
</div>
<div class="gantt-pin" style="left:91%">
<span>{{gantt-pin-span-3}}</span>
<small>{{gantt-pin-small-3}}</small>
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
