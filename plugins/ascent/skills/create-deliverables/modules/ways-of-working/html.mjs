/** HTML views owned by the ways-of-working module. */

import { disclosure, renderDataTable, renderDisclosures, renderProse, typeset } from '../shared/primitives.mjs';

export const RENDERERS = { logistics: renderDataTable, cadence: renderDataTable, 'meeting-cadence': meetingCadence, 'team-norms': renderDisclosures };

function meetingCadence(section) {
  return `<div class="meeting-list">${section.meetings.map((meeting) => disclosure(
    `<strong>${typeset(meeting.title)}</strong><span class="meeting-meta">${typeset(meeting.frequency)} · ${typeset(meeting.owner)}</span><span class="detail-summary">${typeset(meeting.summary)}</span>`,
    `<p><strong>Participants:</strong> ${meeting.participants.map(typeset).join(', ')}</p><div class="prose">${renderProse(meeting.detail)}</div>`,
  )).join('')}</div>`;
}
