import { typeset, renderTableScene, renderStatement, renderNextStepsScene } from '../shared/primitives.mjs';

/**
 * The RAG scorecard is the one view this module doesn't get from a shared
 * primitive. Slalom's palette has no amber or green, so real Green/Amber/Red
 * are a deliberate, documented deviation (see the "Status" note in
 * tokens.css and STATUS_COLORS in validate-brand.mjs). Colour still never
 * carries the value alone: every cell prints "Green"/"Amber"/"Red" as text
 * next to the colour dot, reusing the existing heatmap markup contract
 * (`data-cell` + `.cell__value` + a `.heatmap__legend`) so it is covered by
 * the same accessibility validation as heatmap cells.
 */
const STATUS_LABEL = { green: 'Green', amber: 'Amber', red: 'Red' };

function statusDot(status) {
  return `<span class="status-dot status-dot--${status}" aria-hidden="true"></span>`;
}

function scorecard(section) {
  const rows = section.rows.map((row) => `<tr data-motion-item>
    <th scope="row">${typeset(row.area)}</th>
    <td data-cell><span class="cell">${statusDot(row.status)}<span class="cell__value">${typeset(STATUS_LABEL[row.status])}</span></span></td>
    <td>${row.note ? typeset(row.note) : ''}</td>
  </tr>`).join('');
  return `<div class="module-scene module-scene--scorecard heatmap" data-motion="cell-sweep">
    <div class="heatmap__scroll">
      <table>
        <caption>${typeset(section.title)}</caption>
        <thead><tr><th scope="col">Area</th><th scope="col">Status</th><th scope="col">Note</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <ul class="heatmap__legend">
      <li>${statusDot('green')} Green — on track</li>
      <li>${statusDot('amber')} Amber — at risk</li>
      <li>${statusDot('red')} Red — off track</li>
    </ul>
  </div>`;
}

export const RENDERERS = {
  roster: (section) => renderTableScene(section, 'roster'),
  scorecard,
  'scope-note': (section) => renderStatement(section, 'scope-note'),
  completed: (section) => renderNextStepsScene(section, 'completed'),
  planned: (section) => renderNextStepsScene(section, 'planned'),
  'critical-questions': (section) => renderNextStepsScene(section, 'critical-questions'),
  milestones: (section) => renderTableScene(section, 'milestones'),
};
