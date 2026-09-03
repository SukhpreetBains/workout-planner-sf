/** HTML views owned by the discovery-and-deliverables module. */

import { renderDataTable } from '../shared/primitives.mjs';

export const RENDERERS = { sessions: renderDataTable, deliverables: renderDataTable };
