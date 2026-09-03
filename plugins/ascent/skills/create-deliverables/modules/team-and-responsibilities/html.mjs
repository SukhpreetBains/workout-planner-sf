/** HTML views owned by the team-and-responsibilities module. */

import { renderDataTable } from '../shared/primitives.mjs';

export const RENDERERS = {
  team: renderDataTable,
  'decision-rights': renderDataTable,
};
