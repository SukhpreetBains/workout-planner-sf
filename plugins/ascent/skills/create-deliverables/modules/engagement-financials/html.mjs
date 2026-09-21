import { renderTableScene, renderKpiScene, renderStatement } from '../shared/primitives.mjs';

export const RENDERERS = {
  'contract-summary': (section) => renderKpiScene(section, 'contract-summary'),
  invoices: (section) => renderTableScene(section, 'invoices'),
  'team-effort': (section) => renderTableScene(section, 'team-effort'),
  notes: (section) => renderStatement(section, 'notes'),
};
