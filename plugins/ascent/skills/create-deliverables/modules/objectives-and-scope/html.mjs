/** HTML views owned by the objectives-and-scope module. */

import { esc, renderDataTable, renderProse, toNumeric, typeset } from '../shared/primitives.mjs';

function purpose(section) {
  return `
    <div class="exec-summary" data-motion="fade-up">
      <div class="prose">${renderProse(section.body)}</div>
    </div>`;
}

function successMeasures(section) {
  const tiles = section.items.map((item) => {
    const numeric = toNumeric(item.value);
    const valueAttrs = numeric
      ? ` data-count-to="${esc(numeric.value)}" data-count-decimals="${numeric.decimals}"`
      : '';
    const unit = item.unit ? `<span class="kpi__unit">&nbsp;${typeset(item.unit)}</span>` : '';
    return `
        <li class="kpi" data-motion-item>
          <p class="kpi__value"><span${valueAttrs}>${typeset(item.value)}</span>${unit}</p>
          <p class="kpi__label">${typeset(item.label)}</p>
          <p class="kpi__source">Source: ${typeset(item.source)}</p>
        </li>`;
  }).join('');
  return `
    <ul class="kpi-row" data-motion="count-up">${tiles}
    </ul>`;
}

export const RENDERERS = {
  purpose,
  'success-measures': successMeasures,
  'scope-details': renderDataTable,
};
