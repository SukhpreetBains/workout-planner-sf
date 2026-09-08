/** HTML views owned by the delivery-approach module. */

import { disclosure, esc, renderDataTable, renderProse, typeset } from '../shared/primitives.mjs';

function timeline(section) {
  const phases = section.phases.map((phase) => {
    const outcomes = phase.outcomes.map((outcome) => `<li>${typeset(outcome)}</li>`).join('');
    return `
        <li class="phase">
          <p class="eyebrow phase__window">${typeset(phase.window)}</p>
          <h3 class="subhead">${typeset(phase.name)}</h3>
          <ul class="phase__outcomes">${outcomes}</ul>
        </li>`;
  }).join('');
  return `
    <div class="roadmap" data-motion="path-draw">
      <div class="roadmap__rail">
        <svg class="roadmap__path" viewBox="0 0 1000 48" preserveAspectRatio="none" aria-hidden="true" focusable="false">
          <path d="M4 40C160 40 180 8 340 8 500 8 520 40 680 40 840 40 860 12 996 12"/>
        </svg>
      </div>
      <ol class="roadmap__phases">${phases}
      </ol>
    </div>`;
}

export const RENDERERS = { timeline, 'delivery-model': renderDataTable, 'phase-progression': phaseProgression, 'workstream-schedule': workstreamSchedule };

function phaseProgression(section) {
  const points = section.phases.map((phase, i) => `${(i + 0.5) * 1000 / section.phases.length},${130 - i * 100 / Math.max(1, section.phases.length - 1)}`);
  return `<div class="progression-chart"><svg class="progression-line" viewBox="0 0 1000 160" preserveAspectRatio="none" aria-hidden="true" focusable="false"><polyline points="${points.join(' ')}"/>${points.map((point) => { const [x,y] = point.split(','); return `<circle cx="${x}" cy="${y}" r="7"/>`; }).join('')}</svg><ol class="phase-progression">${section.phases.map((phase, i) => `<li class="progression-phase">
    <div class="progression-marker"><span>${i + 1}</span></div><p class="eyebrow">${typeset(phase.window)}</p><h3 class="subhead">${typeset(phase.name)}</h3><p>${typeset(phase.summary)}</p>
    ${disclosure('Outcomes and milestones', `<ul>${phase.outcomes.map((o) => `<li>${typeset(o)}</li>`).join('')}</ul>${phase.milestones?.length ? `<p><strong>Milestones</strong></p><ul>${phase.milestones.map((m) => `<li>${typeset(m)}</li>`).join('')}</ul>` : ''}`)}
  </li>`).join('')}</ol></div>`;
}
const day = (date) => Date.parse(date) / 86400000;
const dateLabel = (date) => new Intl.DateTimeFormat('en-US', {month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC'}).format(new Date(date));
function workstreamSchedule(section) {
  const total = day(section.end) - day(section.start) + 1;
  const position = (date) => 100 * (day(date) - day(section.start)) / total;
  const rangeStyle = (start, end) => `left:${position(start).toFixed(4)}%;width:${(100 * (day(end) - day(start) + 1) / total).toFixed(4)}%`;
  const tasks = [...section.tasks].sort((a, b) => a.start.localeCompare(b.start));
  const ticks = [];
  let cursor = new Date(section.start);
  while (cursor.toISOString().slice(0, 10) <= section.end) {
    const iso = cursor.toISOString().slice(0, 10);
    ticks.push({ position: position(iso), label: new Intl.DateTimeFormat('en-US', {month: 'short', year: 'numeric', timeZone: 'UTC'}).format(cursor) });
    cursor = new Date(Date.UTC(cursor.getUTCFullYear(), cursor.getUTCMonth() + 1, 1));
  }
  // Limit axis labels on long programmes while retaining the full date scale.
  const labels = ticks.filter((tick, i) => i % Math.ceil(ticks.length / 6) === 0 && tick.position < 90);
  const axis = `<div class="schedule-axis" aria-hidden="true"><span>Activity and owner</span><div>${labels.map((tick) => `<span style="left:${tick.position.toFixed(4)}%">${typeset(tick.label)}</span>`).join('')}</div></div>`;
  const chart = (task) => `<span class="schedule-task-timeline" aria-hidden="true">
    ${labels.map((tick) => `<span class="schedule-gridline" style="left:${tick.position.toFixed(4)}%"></span>`).join('')}
    ${section.blackouts.map((b) => `<span class="schedule-blackout" style="${rangeStyle(b.start,b.end)}"></span>`).join('')}
    <span class="schedule-bar" style="${rangeStyle(task.start,task.end)}"></span>
  </span>`;
  return `<p class="schedule-window">${dateLabel(section.start)} to ${dateLabel(section.end)}</p>
    <p class="schedule-hint">Dates and owners are shown for every activity. Select an activity to read its delivery details.</p>
    <div class="schedule-chronology schedule-workstreams">${section.workstreams.map((stream) => `
      <div class="schedule-stream"><h3 class="subhead">${typeset(stream.name)}</h3><p>${typeset(stream.summary)}</p>
      ${axis}
      ${tasks.filter((task) => task.workstream === stream.id).map((task) => disclosure(
        `<span class="schedule-task-row"><span class="schedule-task-label"><strong>${typeset(task.name)}</strong><span class="schedule-task-dates">${dateLabel(task.start)} to ${dateLabel(task.end)}</span><span class="schedule-task-owner">${typeset(task.owner)}</span></span>${chart(task)}</span>`,
        `<div class="prose">${renderProse(task.detail)}</div>`,
        { className: 'disclosure schedule-task' },
      )).join('')}</div>`).join('')}</div>
    <div class="schedule-events"><div><h3 class="subhead">Milestones</h3>${section.milestones.map((m) => disclosure(`<strong>${typeset(m.name)}</strong><span class="detail-summary">${dateLabel(m.date)}</span>`, `<p>${typeset(m.detail)}</p>`)).join('') || '<p>No milestones specified.</p>'}</div><div><h3 class="subhead">Blackout windows</h3>${section.blackouts.map((b) => `<p><strong>${typeset(b.name)}</strong><br>${dateLabel(b.start)} to ${dateLabel(b.end)}</p>`).join('') || '<p>No blackout windows specified.</p>'}</div></div>`;
}
