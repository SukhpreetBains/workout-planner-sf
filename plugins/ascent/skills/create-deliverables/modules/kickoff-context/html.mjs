/** HTML views owned by the kickoff-context module. */

import { colorBar, esc, renderProse, slalomLine, slug, typeset } from '../shared/primitives.mjs';

function cover(meta, ctx) {
  const surface = ctx.coverSurface;
  const lockup = ctx.clientLogoPath
    ? `<div class="lockup"><img src="${esc(ctx.clientLogoPath)}" alt="${esc(meta.client)}" data-client-asset></div>`
    : '';
  const subtitle = meta.subtitle
    ? `<p class="cover__subtitle">${typeset(meta.subtitle)}</p>`
    : '';
  const authors = (meta.authors ?? []).length
    ? `<div><dt>Prepared by</dt>${meta.authors.map((author) =>
        `<dd>${typeset(author.name)}${author.role ? `, ${typeset(author.role)}` : ''}</dd>`).join('')}</div>`
    : '';
  return `
  <header class="cover surface-${esc(surface)}" data-bar-bg="${esc(surface)}">
    ${slalomLine()}
    <div class="cover__masthead">
      <div class="logo"><img src="${esc(ctx.logoPath)}" alt="Slalom"></div>
      ${lockup}
    </div>
    <div class="cover__body">
      <p class="eyebrow">${typeset(meta.client)}</p>
      <h1 class="display cover__title">${typeset(meta.title)}</h1>
      ${subtitle}
      <dl class="cover__meta">
        <div><dt>Date</dt><dd>${esc(ctx.dateLong)}</dd></div>
        ${authors}
      </dl>
    </div>
    <div class="cover__foot">
      <p class="classification">${typeset(meta.classification)}</p>
      ${colorBar()}
    </div>
  </header>`;
}

function agenda(section) {
  const groupName = `agenda-${slug(section.title ?? 'agenda')}`;
  const items = section.items.map((item, index) => `
        <li class="agenda-item" data-motion-item>
          <details class="agenda-item__disclosure" name="${esc(groupName)}">
            <summary class="agenda-item__summary">
              <span class="agenda-item__index" aria-hidden="true">${index + 1}</span>
              <span>${typeset(item.title)}</span>
              <span class="agenda-item__indicator" aria-hidden="true"></span>
            </summary>
            <div class="agenda-item__card">
              <div class="prose">${renderProse(item.detail)}</div>
            </div>
          </details>
        </li>`).join('');
  return `
    <ol class="agenda" data-motion="stagger-up">${items}
    </ol>`;
}

function workingAgreement(section) {
  const title = section.attribution_title
    ? `<span class="quote__title">${typeset(section.attribution_title)}</span>`
    : '';
  return `
    <figure class="quote" data-motion="fade-up">
      <blockquote class="quote__text">
        <span class="quote__mark" aria-hidden="true">“</span>${typeset(section.quote)}<span class="quote__mark" aria-hidden="true">”</span>
      </blockquote>
      <figcaption class="quote__attrib">
        <span class="quote__name">${typeset(section.name)}</span>
        ${title}
      </figcaption>
    </figure>`;
}

export const RENDERERS = { cover, agenda, 'working-agreement': workingAgreement };
