/** Team views retain ownership here, with shared disclosure behavior. */
import { disclosure, esc, renderDataTable, renderProse, typeset } from '../shared/primitives.mjs';
const roleBody = (role) => `<p class="role-owner">${typeset(role.person ?? 'Role to be assigned')} · ${typeset(role.organization)}</p><div class="prose">${renderProse(role.detail)}</div>`;
function profiles(section, ctx) {
  const teams = new Map();
  for (const role of section.roles) {
    if (!teams.has(role.organization)) teams.set(role.organization, []);
    teams.get(role.organization).push(role);
  }
  return `<div class="team-groups">${[...teams].map(([team, roles]) => `
    <section class="team-group" aria-label="${esc(team)}">
      <h3 class="team-group__title">${typeset(team)}</h3>
      <div class="profile-grid">${roles.map((role) => `<article class="profile">
        ${role.photo ? `<img class="profile__photo" src="${esc(ctx.profilePath(role.photo))}" alt="${esc(role.person ?? role.name)}" data-client-asset>` : ''}
        <h4 class="subhead">${typeset(role.person ?? role.name)}</h4>
        <p>${typeset(role.name)}</p>${role.location ? `<p class="profile__location">${typeset(role.location)}</p>` : ''}
        ${disclosure('Responsibilities', `<p>${typeset(role.summary)}</p>${roleBody(role)}`)}
      </article>`).join('')}</div>
    </section>`).join('')}</div>`;
}

function responsibilities(section) {
  return `<div class="disclosure-list">${section.roles.map((role) => disclosure(`<strong>${typeset(role.name)}</strong><span class="detail-summary">${typeset(role.person ?? 'Role to be assigned')} · ${typeset(role.organization)}<br>${typeset(role.summary)}</span>`,roleBody(role))).join('')}</div>`;
}
const labels = { R: 'Responsible', A: 'Accountable', C: 'Consulted', I: 'Informed' };
function raci(section) {
  return `<div class="raci-list">${section.activities.map((activity) => disclosure(
    `<strong>${typeset(activity.name)}</strong><span class="detail-summary">${typeset(activity.summary)}</span>`,
    renderDataTable({ columns: ['Name', 'Role', 'Accountability'], rows: activity.assignments.map((assignment) => {
      const role = section.roles.find((r) => r.id === assignment.role);
      return { cells: [role.person ?? 'To be assigned', role.name, labels[assignment.responsibility]] };
    }) }),
  )).join('')}</div>`;
}

function operatingModel(section) {
  return `<div class="operating-model">${section.groups.map((group) => `<div class="operating-tier"><div><h3 class="subhead">${typeset(group.name)}</h3><p>${typeset(group.summary)}</p></div><div class="operating-roles">${group.roles.map((id) => {
    const role = section.roles.find((r) => r.id === id);
    return disclosure(`<strong>${typeset(role.name)}</strong><span class="detail-summary">${typeset(role.organization)}</span>`,roleBody(role));
  }).join('')}</div></div>`).join('')}</div>`;
}
export const RENDERERS = { team: renderDataTable, 'decision-rights': renderDataTable, profiles, responsibilities, raci, 'operating-model': operatingModel };
