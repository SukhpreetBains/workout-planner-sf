/** HTML views owned by the raid module. */

import { esc, meter, renderDataTable, renderProse, typeset } from '../shared/primitives.mjs';

const SEVERITY_LEVEL = { high: 3, medium: 2, low: 1 };
const SEVERITY_WORD = { high: 'High', medium: 'Medium', low: 'Low' };
const HEATMAP_SCALE = [
  [1, 'Absent'],
  [2, 'Emerging'],
  [3, 'Established'],
  [4, 'Advanced'],
  [5, 'Leading'],
];

function summary(section, ctx) {
  const intro = section.body ? `<div class="prose measure">${renderProse(section.body)}</div>` : '';
  const cards = section.findings.map((finding) => {
    const icon = finding.icon
      ? `<img class="finding__icon" src="${esc(ctx.iconPath(finding.icon))}" alt="">`
      : '';
    const severity = finding.severity
      ? `<p class="severity">${meter(SEVERITY_LEVEL[finding.severity], 3, 'meter--tall')}<span>${SEVERITY_WORD[finding.severity]} severity</span></p>`
      : '';
    return `
        <article class="finding" data-motion-item>
          <div class="finding__head">
            <div class="finding__title">${icon}<h3 class="subhead">${typeset(finding.theme)}</h3></div>
            ${severity}
          </div>
          <div class="finding__fields">
            <dl class="finding__field">
              <dt>Evidence</dt>
              <dd>${typeset(finding.evidence)}</dd>
            </dl>
            <dl class="finding__field">
              <dt>Implication</dt>
              <dd class="finding__implication">${typeset(finding.implication)}</dd>
            </dl>
          </div>
        </article>`;
  }).join('');
  return `${intro}
    <div class="findings" data-motion="stagger-up">${cards}
    </div>`;
}

function riskProfile(section) {
  const cols = section.columns.length;
  const head = section.columns.map((column) => `<th scope="col">${typeset(column)}</th>`).join('');
  const body = section.rows.map((row) => {
    const cells = row.values.map((value) => `
            <td data-cell>
              <span class="cell">${meter(value, 5)}<span class="cell__value">${value}<span class="visually-hidden"> out of 5</span></span></span>
            </td>`).join('');
    const note = row.note ? `<p class="heatmap__note">${typeset(row.note)}</p>` : '';
    return `
          <tr>
            <th scope="row">${typeset(row.capability)}${note}</th>${cells}
          </tr>`;
  }).join('');
  const legend = HEATMAP_SCALE
    .map(([value, label]) => `<li>${meter(value, 5)}<span>${value} — ${label}</span></li>`)
    .join('');
  return `
    <div class="heatmap" data-motion="cell-sweep" data-motion-cols="${cols}">
      <div class="heatmap__scroll">
        <table>
          <caption class="visually-hidden">${typeset(section.title)}, rated 1 to 5</caption>
          <thead><tr><th scope="col">Capability</th>${head}</tr></thead>
          <tbody>${body}
          </tbody>
        </table>
      </div>
      <ul class="heatmap__legend">${legend}</ul>
    </div>`;
}

export const RENDERERS = { summary, details: renderDataTable, 'risk-profile': riskProfile };
