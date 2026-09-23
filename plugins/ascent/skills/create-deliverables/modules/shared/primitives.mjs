/** Shared HTML primitives for module-owned renderers. */

export const COLOR_BAR_ORDER = ['blue', 'cyan', 'coral-red', 'purple', 'chartreuse'];

export function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

export const typeset = (value) => esc(value);

export function slug(value) {
  return String(value ?? '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

export const moduleIndex = (index) => String(index + 1).padStart(2, '0');
export const rowCell = (row, index) => typeset(row?.cells?.[index] ?? '');
export const rawCell = (row, index) => String(row?.cells?.[index] ?? '');

export function initials(value) {
  return String(value ?? '').split(/\s+/).filter(Boolean).slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '').join('');
}

export function stateClass(value) {
  const normal = slug(value);
  if (/high|blocked|risk|issue/.test(normal)) return 'is-alert';
  if (/ready|done|complete|confirmed|approved/.test(normal)) return 'is-ready';
  return 'is-watch';
}

export function weekRange(value, fallback = 1) {
  const values = String(value ?? '').match(/\d+/g)?.map(Number) ?? [];
  const start = Math.max(1, Math.min(16, values[0] ?? fallback));
  const end = Math.max(start, Math.min(16, values[1] ?? start));
  return { start, span: end - start + 1 };
}

export function renderProse(value) {
  const lines = String(value ?? '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (!lines.length) return '';
  const parts = [];
  let list = [];
  const flush = () => {
    if (!list.length) return;
    parts.push(`<ul>${list.map((item) => `<li>${typeset(item)}</li>`).join('')}</ul>`);
    list = [];
  };
  for (const line of lines) {
    if (/^[-*]\s+/.test(line)) list.push(line.replace(/^[-*]\s+/, ''));
    else {
      flush();
      parts.push(`<p>${typeset(line)}</p>`);
    }
  }
  flush();
  return `<div class="prose">${parts.join('')}</div>`;
}

export function renderCover(meta, ctx) {
  const authors = (meta.authors ?? []).map((author) => `<div><dt>${typeset(author.role || 'Prepared by')}</dt><dd>${typeset(author.name)}</dd></div>`).join('');
  const clientLockup = ctx.clientLogoPath ? `<div class="lockup"><img data-authored-asset src="${esc(ctx.clientLogoPath)}" alt="${typeset(meta.client)}"></div>` : '';
  const background = ctx.coverBackground ? `<img class="cover__background" data-authored-asset src="${esc(ctx.coverBackground)}" alt="">` : '';
  return `
    <header class="cover surface-blue${background ? ' cover--image' : ''}" data-bar-bg="blue">
      ${background}
      <div class="cover__masthead"><div class="logo"><img src="${esc(ctx.logoPath)}" alt="Slalom"></div>${clientLockup}</div>
      <div class="cover__body" data-motion="fade-up">
        <p class="eyebrow">Project kickoff</p>
        <h1 class="display cover__title">${typeset(meta.title)}</h1>
        ${meta.subtitle ? `<p class="cover__subtitle">${typeset(meta.subtitle)}</p>` : ''}
        <dl class="cover__meta"><div><dt>Prepared for</dt><dd>${typeset(meta.client)}</dd></div><div><dt>Date</dt><dd>${typeset(ctx.dateLong)}</dd></div>${authors}</dl>
      </div>
      <div class="cover__foot"><p class="classification">${typeset(meta.classification)}</p><div class="color-bar" data-motion="color-bar-draw" aria-hidden="true"><span class="color-bar__swatch color-bar__swatch--blue"></span><span class="color-bar__swatch color-bar__swatch--cyan"></span><span class="color-bar__swatch color-bar__swatch--coral-red"></span><span class="color-bar__swatch color-bar__swatch--purple"></span><span class="color-bar__swatch color-bar__swatch--chartreuse"></span></div></div>
    </header>`;
}

export function renderStatement(section, modifier = 'statement') {
  return `<div class="module-scene module-scene--${esc(modifier)}" data-motion="fade-up">${renderProse(section.body)}</div>`;
}

export function renderAgendaCards(section, modifier = 'agenda') {
  const items = section.items.map((item, index) => `
    <details class="module-card module-card--agenda" data-motion-item${index === 0 ? ' open' : ''}>
      <summary><span class="module-index">${String(index + 1).padStart(2, '0')}</span><span><strong>${typeset(item.title)}</strong><small>${typeset(item.detail)}</small></span><span class="module-plus" aria-hidden="true">+</span></summary>
      <p>${typeset(item.detail)}</p>
    </details>`).join('');
  return `<div class="module-scene module-scene--${esc(modifier)} module-card-grid" data-motion="stagger-up">${items}</div>`;
}

export function renderKpiScene(section, modifier = 'outcomes') {
  const items = section.items.map((item) => {
    const numeric = typeof item.value === 'number' ? ` data-count-to="${esc(item.value)}"` : '';
    return `<article class="module-card module-card--kpi" data-motion-item><p class="module-kpi"><span${numeric}>${typeset(item.value)}</span>${item.unit ? `<span>${typeset(item.unit)}</span>` : ''}</p><h3>${typeset(item.label)}</h3><small>${typeset(item.source)}</small></article>`;
  }).join('');
  return `<div class="module-scene module-scene--${esc(modifier)} module-card-grid" data-motion="count-up">${items}</div>`;
}

export function renderFindingScene(section, modifier = 'context', ctx = null) {
  const items = section.findings.map((finding, index) => {
    const severity = finding.severity ? `${finding.severity[0].toUpperCase()}${finding.severity.slice(1)}` : null;
    const icon = finding.icon && ctx ? `<img class="finding__icon" src="${esc(ctx.iconPath(finding.icon))}" alt="">` : '';
    return `<article class="module-card module-card--finding" data-motion-item><div class="module-finding-head">${icon}<p class="module-index">${String(index + 1).padStart(2, '0')}</p></div><h3>${typeset(finding.theme)}</h3><p>${typeset(finding.evidence)}</p><strong>${typeset(finding.implication)}</strong>${severity ? `<div class="severity"><span>${typeset(severity)} severity</span></div>` : ''}</article>`;
  }).join('');
  return `<div class="module-scene module-scene--${esc(modifier)} module-card-grid" data-motion="stagger-up">${section.body ? renderProse(section.body) : ''}${items}</div>`;
}

export function renderTableScene(section, modifier = 'table') {
  const head = section.columns.map((column) => `<th scope="col">${typeset(column)}</th>`).join('');
  const rows = section.rows.map((row) => `<tr data-motion-item>${row.cells.map((cell, index) => index === 0 ? `<th scope="row">${typeset(cell)}</th>` : `<td>${typeset(cell)}</td>`).join('')}</tr>`).join('');
  return `<div class="module-scene module-scene--${esc(modifier)} data-table" data-motion="fade-up"><div class="data-table__scroll"><table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div></div>`;
}

export function renderRoadmapScene(section, modifier = 'roadmap') {
  const phases = section.phases.map((phase, index) => `<article class="module-card module-card--phase phase" data-motion-item><span class="module-index">${String(index + 1).padStart(2, '0')}</span><small>${typeset(phase.window)}</small><h3>${typeset(phase.name)}</h3><ul>${phase.outcomes.map((outcome) => `<li>${typeset(outcome)}</li>`).join('')}</ul></article>`).join('');
  return `<div class="module-scene module-scene--${esc(modifier)} roadmap" data-motion="path-draw"><svg class="roadmap__path" viewBox="0 0 1000 80" role="img" aria-label="Progression from the first phase to the last"><path d="M20 40 H980"></path></svg><div class="module-phase-grid">${phases}</div></div>`;
}

export function renderNextStepsScene(section, modifier = 'next-steps') {
  const items = section.items.map((item, index) => `<li class="module-card module-card--step" data-motion-item><span class="module-index">${String(index + 1).padStart(2, '0')}</span><p>${typeset(item)}</p></li>`).join('');
  return `<ol class="module-scene module-scene--${esc(modifier)} module-step-list" data-motion="stagger-up">${items}</ol>`;
}
