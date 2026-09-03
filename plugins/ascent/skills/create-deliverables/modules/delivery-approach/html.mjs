/** HTML views owned by the delivery-approach module. */

import { renderDataTable, typeset } from '../shared/primitives.mjs';

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

export const RENDERERS = { timeline, 'delivery-model': renderDataTable };
