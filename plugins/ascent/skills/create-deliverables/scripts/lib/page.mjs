/** Page chrome and system-owned views around module-rendered content. */

import { resolveSectionType } from './content.mjs';
import { esc, renderProse, slug, typeset } from '../../modules/shared/primitives.mjs';

const EYEBROW = {
  purpose: 'Purpose',
  'kpi-row': 'By the numbers',
  'theme-group': 'What we heard',
  roadmap: 'Roadmap',
  quote: 'Client voice',
  heatmap: 'Assessment',
  'next-steps': 'Next steps',
  agenda: 'Agenda',
  'gap-summary': 'Incomplete draft',
  'open-questions': 'Open questions',
};

const FALLBACK_TITLE = {
  purpose: 'Purpose & scope',
  'kpi-row': 'By the numbers',
  'theme-group': 'What we heard',
  roadmap: 'Roadmap',
  quote: 'Client voice',
  heatmap: 'Assessment',
  'next-steps': 'Next steps',
  agenda: 'Agenda',
  table: 'Details',
  'gap-summary': 'Required information still open',
  'open-questions': 'Open questions',
};

export function railLabel(section) {
  const type = resolveSectionType(section.type);
  return section.title || FALLBACK_TITLE[type] || type;
}

export function sectionId(section, index) {
  const base = slug(section.title) || slug(resolveSectionType(section.type));
  return `s${index + 1}-${base || 'section'}`;
}

export function renderRail(entries) {
  if (!entries.length) return '';
  const link = (entry, position, current = false) => entry
    ? `<a class="rail__link rail__link--${position}" href="#${esc(entry.id)}"${current ? ' aria-current="location"' : ''}>${typeset(entry.label)}</a>`
    : `<span class="rail__link rail__link--${position}" hidden></span>`;
  // The document owns the complete section list while the visual rail keeps
  // only the previous, current, and next sections in view.
  const serializedEntries = JSON.stringify(entries).replace(/</g, '\\u003c');
  return `
    <nav class="rail" data-motion="scroll-sync" aria-label="Section navigation">
      <div class="rail__track"><div class="rail__fill"></div></div>
      <div class="rail__nav">
        ${link(null, 'previous')}
        ${link(entries[0], 'current', true)}
        ${link(entries[1], 'next')}
      </div>
      <script class="rail__entries" type="application/json">${serializedEntries}</script>
    </nav>`;
}

export function renderFooter(meta, ctx) {
  return `
    <footer class="footer">
      <div class="footer__inner">
        <div class="logo"><img src="${esc(ctx.footerLogoPath)}" alt="Slalom"></div>
        <div class="footer__meta">
          <p class="classification">${typeset(meta.classification)}</p>
          <p>Prepared for ${typeset(meta.client)} · ${esc(ctx.dateLong)}</p>
        </div>
      </div>
    </footer>`;
}

function renderGapSummary(section) {
  const byModule = new Map();
  for (const item of section.items) {
    if (!byModule.has(item.module)) byModule.set(item.module, []);
    byModule.get(item.module).push(item);
  }
  const groups = [...byModule.entries()].map(([module, items]) => `
        <li class="gap-summary__group">
          <h3 class="subhead">${typeset(module)}</h3>
          <p>${items.length} required answer${items.length === 1 ? '' : 's'} still open</p>
        </li>`).join('');
  return `
    <div class="gap-summary" role="status">
      <p class="gap-summary__lead">This microsite was generated with required information still unresolved. Empty sections are intentional and must not be treated as confirmed project facts.</p>
      <ul class="gap-summary__groups">${groups}
      </ul>
    </div>`;
}

function renderOpenQuestions(items) {
  const questions = items.map((item) => `
        <li class="open-question">
          <p class="eyebrow">Required answer missing</p>
          <p class="open-question__prompt">${typeset(item.prompt)}</p>
          <p class="open-question__id">${typeset(item.id)}</p>
        </li>`).join('');
  return `
    <aside class="open-questions" aria-label="Required information still open">
      <h3 class="subhead">This section is incomplete</h3>
      <ul>${questions}
      </ul>
    </aside>`;
}

const SYSTEM_RENDERERS = {
  'gap-summary': renderGapSummary,
  'open-questions': (section) => renderOpenQuestions(section.items),
};

export function renderSection(section, index, ctx, renderer = null) {
  const type = resolveSectionType(section.type);
  const component = renderer ?? SYSTEM_RENDERERS[type];
  if (!component) throw new Error(`internal: no module renderer registered for \`${type}\``);

  const id = sectionId(section, index);
  const title = section.title ?? FALLBACK_TITLE[type];
  const eyebrow = EYEBROW[type];
  const titled = type !== 'quote';
  const illustration = ctx.illustrations?.get(`${section.module}:${section.view}`);
  const head = titled
    ? `
      <div class="section__head${illustration ? ' section__head--illustrated' : ''}">
        ${illustration ? `<img class="section__illustration" src="${esc(illustration)}" alt="">` : ''}
        ${eyebrow ? `<p class="eyebrow">${typeset(eyebrow)}</p>` : ''}
        <h2 class="headline" id="${esc(id)}-title">${typeset(title)}</h2>
      </div>`
    : '';
  const labelling = titled
    ? `aria-labelledby="${esc(id)}-title"`
    : `aria-label="${esc(title)}"`;

  const openQuestions = section._openQuestions?.length
    ? renderOpenQuestions(section._openQuestions)
    : '';
  const previewLabel = ctx.structurePreview && section.module
    ? `<p class="eyebrow">Module: ${typeset(ctx.moduleTitles.get(section.module) ?? section.module)}</p>`
    : '';
  const previewAttribute = ctx.structurePreview && section.module
    ? ` data-preview-module="${esc(section.module)}"`
    : '';

  return `
  <section class="section surface-white" id="${esc(id)}" ${labelling}${previewAttribute}>
    <div class="section__inner">${previewLabel}${head}${component(section, ctx)}${openQuestions}
    </div>
  </section>`;
}
