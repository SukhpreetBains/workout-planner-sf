import { renderTableScene } from '../shared/primitives.mjs';

export const RENDERERS = {
  'escalation-log': (section) => renderTableScene(section, 'escalation-log'),
};
