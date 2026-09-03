/** HTML views owned by the immediate-next-steps module. */

import { typeset } from '../shared/primitives.mjs';

function actions(section) {
  const items = section.items.map((item, index) => `
        <li class="next-step" data-motion-item>
          <span class="next-step__index" aria-hidden="true">${index + 1}</span>
          <span>${typeset(item)}</span>
        </li>`).join('');
  return `
    <ol class="next-steps" data-motion="stagger-up">${items}
    </ol>`;
}

export const RENDERERS = { actions };
