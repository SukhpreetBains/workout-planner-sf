/** Interactive timeline view owned by the timeline-roadmap module. */

import { typeset } from '../shared/primitives.mjs';

const DAY = 86_400_000;

function parseDay(value) {
  const [year, month, day] = value.split('-').map(Number);
  return Date.UTC(year, month - 1, day);
}

function formatAxisDate(value) {
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
    .format(new Date(value));
}

function phaseDates(phase) {
  return phase.start && phase.end
    ? `<span class="execution-map__dates"><time datetime="${typeset(phase.start)}">${formatAxisDate(parseDay(phase.start))}</time><span aria-hidden="true">–</span><time datetime="${typeset(phase.end)}">${formatAxisDate(parseDay(phase.end))}</time></span>`
    : typeset(phase.window);
}

function phaseDetail(phase) {
  const activities = (phase.activities ?? []).map((activity) => `
                <li class="timeline-detail__activity">
                  <strong>${typeset(activity.title)}</strong>${activity.detail ? `<span>${typeset(activity.detail)}</span>` : ''}
                </li>`).join('');
  const outcomes = phase.outcomes.map((outcome) => `<li>${typeset(outcome)}</li>`).join('');
  const milestones = (phase.milestones ?? []).map((milestone) => `
                <li class="timeline-detail__milestone">
                  ${milestone.date ? `<time datetime="${typeset(milestone.date)}">${typeset(milestone.date)}</time>` : ''}
                  <span><strong>${typeset(milestone.title)}</strong>${milestone.detail ? `<span>${typeset(milestone.detail)}</span>` : ''}</span>
                </li>`).join('');

  return `
            <div class="timeline-detail">
              <div class="timeline-detail__intro">
                <p class="eyebrow">${phase.summary ? 'Phase purpose' : 'Phase outcomes'}</p>
                ${phase.summary ? `<p class="timeline-detail__summary">${typeset(phase.summary)}</p>` : ''}
              </div>
              ${activities ? `<div class="timeline-detail__group">
                <p class="eyebrow">What happens</p>
                <ol class="timeline-detail__activities">${activities}
                </ol>
              </div>` : ''}
              <div class="timeline-detail__group">
                <p class="eyebrow">Outcomes</p>
                <ul class="timeline-detail__outcomes">${outcomes}</ul>
              </div>
              ${milestones ? `<div class="timeline-detail__group">
                <p class="eyebrow">Milestones</p>
                <ul class="timeline-detail__milestones">${milestones}
                </ul>
              </div>` : ''}
              ${phase.decision ? `<div class="timeline-detail__decision"><span>Decision point</span><strong>${typeset(phase.decision)}</strong></div>` : ''}
            </div>`;
}

function ganttScale(section) {
  const dated = section.phases.every((phase) => phase.start && phase.end);
  if (!dated) return { dated: false, ticks: section.phases.map((phase) => phase.window) };

  const starts = section.phases.map((phase) => parseDay(phase.start));
  const ends = section.phases.map((phase) => parseDay(phase.end) + DAY);
  const start = Math.min(...starts);
  const end = Math.max(...ends);
  const duration = Math.max(DAY, end - start);
  const requested = section.time_scale ?? 'auto';
  const scale = requested === 'auto'
    ? (duration <= 70 * DAY ? 'week' : duration <= 180 * DAY ? 'two-week' : 'month')
    : requested;
  const step = scale === 'week' ? 7 * DAY : scale === 'two-week' ? 14 * DAY : 30 * DAY;
  const tickCount = Math.max(2, Math.min(12, Math.ceil(duration / step)));
  const ticks = Array.from({ length: tickCount }, (_, index) => {
    const at = start + (duration * index) / Math.max(1, tickCount - 1);
    return formatAxisDate(at);
  });
  return { dated: true, start, duration, ticks };
}

function executionMap(section) {
  const scale = ganttScale(section);
  const mapId = `execution-map-${section.phases.map((phase) => phase.name).join('-').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')}`;
  const horizon = scale.dated ? scale.ticks : section.phases.map((phase) => phase.window);
  const activeByDefault = 1;
  const rows = section.phases.map((phase, index) => {
    const start = scale.dated ? Math.max(1, Math.floor(((parseDay(phase.start) - scale.start) / scale.duration) * horizon.length) + 1) : index + 1;
    const end = scale.dated ? Math.min(horizon.length, Math.ceil((((parseDay(phase.end) + DAY) - scale.start) / scale.duration) * horizon.length)) : index + 1;
    const span = Math.max(1, end - start + 1);
    return `
        <li class="execution-map__row" data-motion-item>
          <div class="execution-map__label">
            <span>${String(index + 1).padStart(2, '0')}</span>
            <strong>${typeset(phase.name)}</strong>
            <small>${typeset(phase.summary ?? phase.window)}</small>
          </div>
          <div class="execution-map__track">
            <button class="execution-map__bar" type="button" style="--phase-start:${start};--phase-span:${span}" data-phase-start="${start}" data-phase-end="${start + span - 1}" data-tooltip="${typeset(phase.name)}" title="${typeset(phase.name)}" aria-expanded="false" aria-controls="${mapId}-inspector">
              <span>${typeset(phase.name)}</span><small>${phaseDates(phase)}</small>
            </button>
            <div class="execution-map__source" hidden>${phaseDetail(phase)}</div>
          </div>
        </li>`;
  }).join('');
  const ticks = horizon.map((tick, index) => `<span>${String(index + 1).padStart(2, '0')}<small>${typeset(tick)}</small></span>`).join('');

  return `
    <div class="execution-map" style="--timeline-divisions:${horizon.length};--active-period:${activeByDefault}" data-component="execution_map" data-motion="execution-map-reveal" data-time-scale="${typeset(section.time_scale ?? 'auto')}" data-calendar-scaled="${scale.dated}">
      <div class="execution-map__toolbar">
        <div><p class="eyebrow">Execution map</p><h3>${scale.dated ? 'Explore the delivery horizon' : 'Ordered phase sequence'}</h3><p class="execution-map__context" aria-live="polite">Period 01 · Select a phase to inspect its work, outcomes, and decision point.</p></div>
        <label class="execution-map__scrubber"><span>01</span><input type="range" min="1" max="${horizon.length}" value="${activeByDefault}" aria-label="Explore the execution map by period"><span>${String(horizon.length).padStart(2, '0')}</span></label>
      </div>
      <div class="execution-map__grid">
        <div class="execution-map__periods" aria-hidden="true">${ticks}</div>
        <ol class="execution-map__rows">${rows}</ol>
        <div class="execution-map__playhead" aria-hidden="true"></div>
      </div>
      <p class="execution-map__prompt"><strong>Select a phase bar</strong> to reveal its detail.</p>
      <section class="execution-map__inspector" id="${mapId}-inspector" aria-live="polite" hidden>
        <button class="execution-map__collapse" type="button">Collapse phase details <span aria-hidden="true">↑</span></button>
        <div class="execution-map__inspector-content"></div>
      </section>
    </div>`;
}

export const RENDERERS = { timeline: executionMap };
