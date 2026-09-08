/** Structured delivery views shared across templates. */
const text = { type: 'string', required: true };
const optional = { type: 'string' };
const strings = { type: 'stringlist', required: true, min: 1 };
const list = (of, min = 1) => ({ type: 'list', required: true, min, of });
const role = { id: text, name: text, organization: text, summary: text, detail: { type: 'prose', required: true }, person: optional, location: optional, photo: optional };
const item = { title: text, summary: text, detail: { type: 'prose', required: true } };
export const DELIVERY_SCHEMA = {
  profiles: { title: text, roles: list(role) },
  'role-details': { title: text, roles: list(role) },
  raci: { title: text, roles: list(role), activities: list({ name: text, summary: text, assignments: list({ role: text, responsibility: { ...text, enum: ['R', 'A', 'C', 'I'] } }) }) },
  'operating-model': { title: text, roles: list(role), groups: list({ name: text, summary: text, roles: strings }) },
  disclosures: { title: text, items: list(item) },
  'meeting-cadence': { title: text, meetings: list({ ...item, frequency: text, owner: text, participants: strings }) },
  'phase-progression': { title: text, phases: list({ name: text, window: text, summary: text, outcomes: strings, milestones: { type: 'stringlist' } }) },
  'workstream-schedule': { title: text, start: text, end: text, workstreams: list({ id: text, name: text, summary: text }), tasks: list({ id: text, workstream: text, name: text, start: text, end: text, owner: text, detail: { type: 'prose', required: true } }), milestones: list({ name: text, date: text, detail: text }, 0), blackouts: list({ name: text, start: text, end: text }, 0) },
  workflow: { title: text, roles: list({ id: text, name: text }), stages: list({ id: text, name: text, summary: text, detail: { type: 'prose', required: true }, roles: strings }), transitions: list({ from: text, to: text, label: text }) },
};

export function validateDelivery(section, where, problems) {
  if (!DELIVERY_SCHEMA[section.type]) return;
  const error = (message) => problems.push(`${where}: ${message}`);
  const unique = (items, label) => {
    const ids = (items ?? []).map((item) => item.id);
    if (new Set(ids).size !== ids.length) error(`${label} identifiers must be unique`);
    return new Set(ids);
  };
  const roles = unique(section.roles, 'role');
  const checkRole = (id) => { if (!roles.has(id)) error(`unknown role ${id}`); };
  for (const role of section.roles ?? []) {
    if (role.photo && (!/\.(png|jpe?g|webp)$/i.test(role.photo) || /^(?:[a-z]+:|\/)/i.test(role.photo) || role.photo.split(/[\\/]/).includes('..'))) error('profile photo must be a relative local PNG, JPEG, or WebP path');
  }
  for (const group of section.groups ?? []) group.roles.forEach(checkRole);
  for (const activity of section.activities ?? []) {
    const ids = activity.assignments.map((a) => a.role);
    if (new Set(ids).size !== ids.length) error('an activity assigns each role at most once');
    activity.assignments.forEach((a) => checkRole(a.role));
    if (!activity.assignments.some((a) => a.responsibility === 'A')) error('each RACI activity needs an accountable role');
    if (!activity.assignments.some((a) => a.responsibility === 'R')) error('each RACI activity needs a responsible role');
  }
  if (section.type === 'workflow') {
    const stages = unique(section.stages, 'stage');
    section.stages.forEach((s) => s.roles.forEach(checkRole));
    section.transitions.forEach((t) => { if (!stages.has(t.from) || !stages.has(t.to)) error('transition references an unknown stage'); });
  }
  if (section.type === 'workstream-schedule') {
    const validDate = (value) => /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
    const range = (item) => {
      if (!validDate(item.start) || !validDate(item.end)) error('schedule dates must be real ISO calendar dates');
      else if (item.start > item.end) error('schedule start must not follow end');
      else if (item.start < section.start || item.end > section.end) error('schedule item is outside the schedule window');
    };
    range(section);
    const streams = unique(section.workstreams, 'workstream');
    unique(section.tasks, 'task');
    section.tasks.forEach((t) => { range(t); if (!streams.has(t.workstream)) error('task references an unknown workstream'); });
    section.blackouts.forEach(range);
    section.milestones.forEach((m) => {
      if (!validDate(m.date)) error('milestone date must be a real ISO calendar date');
      else if (m.date < section.start || m.date > section.end) error('milestone is outside the schedule window');
    });
  }
}
