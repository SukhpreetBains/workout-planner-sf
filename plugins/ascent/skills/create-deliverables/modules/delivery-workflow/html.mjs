/** Work-item progression and agreed readiness, independent of project phases. */
import { disclosure, renderDisclosures, renderProse, typeset } from '../shared/primitives.mjs';
function pipeline(section) {
  return `<ol class="workflow">${section.stages.map((stage) => `<li class="workflow-stage">
    <div class="workflow-chevron"><h3>${typeset(stage.name)}</h3></div>
    <p class="workflow-roles">${stage.roles.map((id) => typeset(section.roles.find((r) => r.id === id).name)).join(' · ')}</p>
    <p>${typeset(stage.summary)}</p>
    ${disclosure(`<span class="visually-hidden">More about ${typeset(stage.name)}</span>`, `<div class="prose">${renderProse(stage.detail)}</div><p><strong>Next transitions</strong></p><ul>${section.transitions.filter((t) => t.from === stage.id).map((t) => `<li>${typeset(t.label)}: ${typeset(section.stages.find((s) => s.id === t.to).name)}</li>`).join('') || '<li>End of this workflow</li>'}</ul>`)}
  </li>`).join('')}</ol>`;
}
export const RENDERERS = { pipeline, readiness: renderDisclosures };
