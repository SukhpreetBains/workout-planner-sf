/**
 * components.mjs — the component registry.
 *
 * Every component is a pure function `(section, ctx) => htmlString`, registered
 * by section type. Components emit semantic HTML, declare motion with a
 * `data-motion` attribute, and never carry an inline colour or an inline style.
 *
 * `cover`, `progress-rail` and `footer` are injected by the archetype rather
 * than authored in `sections`, so they take the document meta instead.
 */

import { resolveSectionType } from './content.mjs';

/* ==========================================================================
   HTML helpers
   ========================================================================== */

export function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Curly smart quotes and dashes, per the brand's typesetting guidance. */
export function typeset(text) {
  return esc(text)
    .replace(/(^|[\s(\[])&#39;/g, '$1‘')
    .replace(/&#39;/g, '’')
    .replace(/(^|[\s(\[])&quot;/g, '$1“')
    .replace(/&quot;/g, '”')
    .replace(/ -- /g, ' — ');
}

const slug = (text) =>
  String(text ?? '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48);

/**
 * A markdown subset: blank-line-separated paragraphs, `- ` bullet lists,
 * `**bold**` and `*italic*`. Anything else is escaped and rendered as text —
 * content is authored prose, not a template language.
 */
export function renderProse(text) {
  const blocks = String(text ?? '').replace(/\r\n?/g, '\n').trim().split(/\n{2,}/);
  const out = [];
  for (const block of blocks) {
    const lines = block.split('\n').map((l) => l.trim()).filter(Boolean);
    if (!lines.length) continue;
    if (lines.every((l) => /^[-*]\s+/.test(l))) {
      const items = lines.map((l) => `<li>${inline(l.replace(/^[-*]\s+/, ''))}</li>`);
      out.push(`<ul>${items.join('')}</ul>`);
    } else {
      out.push(`<p>${inline(lines.join(' '))}</p>`);
    }
  }
  return out.join('');
}

function inline(text) {
  return typeset(text)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
}

/** A filled-step meter. Meaning always travels with a text label beside it. */
function meter(on, total, extraClass = '') {
  const steps = [];
  for (let i = 1; i <= total; i++) {
    steps.push(`<span class="meter__step${i <= on ? ' meter__step--on' : ''}"></span>`);
  }
  return `<span class="meter${extraClass ? ` ${extraClass}` : ''}" aria-hidden="true">${steps.join('')}</span>`;
}

const SEVERITY_LEVEL = { high: 3, medium: 2, low: 1 };
const SEVERITY_WORD = { high: 'High', medium: 'Medium', low: 'Low' };

/** The five swatches, always in the brand order, never reordered. */
export const COLOR_BAR_ORDER = ['blue', 'cyan', 'coral-red', 'purple', 'chartreuse'];

export function colorBar() {
  const swatches = COLOR_BAR_ORDER
    .map((name) => `<span class="color-bar__swatch color-bar__swatch--${name}"></span>`)
    .join('');
  return `<div class="color-bar" data-motion="color-bar-draw" aria-hidden="true">${swatches}</div>`;
}

/** A bold single Slalom line: decorative, aria-hidden, exempt from contrast. */
export function slalomLine() {
  return [
    '<svg class="slalom-line" data-motion="line-draw" viewBox="0 0 600 400"',
    ' preserveAspectRatio="xMidYMax slice" aria-hidden="true" focusable="false">',
    '<path d="M-20 392C110 392 132 236 214 168 296 100 372 168 430 128 488 88 500 24 620 8"/>',
    '</svg>',
  ].join('');
}

/* ==========================================================================
   Section chrome
   ========================================================================== */

const EYEBROW = {
  'exec-summary': 'Summary',
  'kpi-row': 'By the numbers',
  'theme-group': 'What we heard',
  recommendations: 'Recommendations',
  roadmap: 'Roadmap',
  quote: 'Client voice',
  heatmap: 'Assessment',
  'next-steps': 'Next steps',
  methodology: 'Method',
};

const FALLBACK_TITLE = {
  'exec-summary': 'In brief',
  'kpi-row': 'By the numbers',
  'theme-group': 'What we heard',
  recommendations: 'Recommendations',
  roadmap: 'Roadmap',
  quote: 'Client voice',
  heatmap: 'Assessment',
  'next-steps': 'Next steps',
  methodology: 'How we got here',
};

/** The label a section contributes to the progress rail. */
export function railLabel(section) {
  const type = resolveSectionType(section.type);
  return section.title || FALLBACK_TITLE[type] || type;
}

export function sectionId(section, index) {
  const base = slug(section.title) || slug(resolveSectionType(section.type));
  return `s${index + 1}-${base || 'section'}`;
}

/* ==========================================================================
   Components
   ========================================================================== */

export const COMPONENTS = {
  'exec-summary': (section) => `
      <div class="exec-summary" data-motion="fade-up">
        <div class="prose">${renderProse(section.body)}</div>
      </div>`,

  'kpi-row': (section) => {
    const tiles = section.items.map((item) => {
      const numeric = toNumeric(item.value);
      const valueAttrs = numeric
        ? ` data-count-to="${esc(numeric.value)}" data-count-decimals="${numeric.decimals}"`
        : '';
      const unit = item.unit ? `<span class="kpi__unit">&nbsp;${typeset(item.unit)}</span>` : '';
      return `
          <li class="kpi" data-motion-item>
            <p class="kpi__value"><span${valueAttrs}>${typeset(item.value)}</span>${unit}</p>
            <p class="kpi__label">${typeset(item.label)}</p>
            <p class="kpi__source">Source: ${typeset(item.source)}</p>
          </li>`;
    }).join('');
    return `
      <ul class="kpi-row" data-motion="count-up">${tiles}
      </ul>`;
  },

  'theme-group': (section, ctx) => {
    const intro = section.body ? `<div class="prose measure">${renderProse(section.body)}</div>` : '';
    const cards = section.findings.map((finding) => {
      const icon = finding.icon
        ? `<img class="finding__icon" src="${esc(ctx.iconPath(finding.icon))}" alt="">`
        : '';
      const severity = finding.severity
        ? `<p class="severity">${meter(SEVERITY_LEVEL[finding.severity], 3, 'meter--tall')}<span>${SEVERITY_WORD[finding.severity]} severity</span></p>`
        : '';
      return `
          <article class="finding" data-motion-item>
            <div class="finding__head">
              <div class="finding__title">${icon}<h3 class="subhead">${typeset(finding.theme)}</h3></div>
              ${severity}
            </div>
            <div class="finding__fields">
              <dl class="finding__field">
                <dt>Evidence</dt>
                <dd>${typeset(finding.evidence)}</dd>
              </dl>
              <dl class="finding__field">
                <dt>Implication</dt>
                <dd class="finding__implication">${typeset(finding.implication)}</dd>
              </dl>
            </div>
          </article>`;
    }).join('');
    return `${intro}
      <div class="findings" data-motion="stagger-up">${cards}
      </div>`;
  },

  recommendations: (section) => {
    const items = section.items.map((item, i) => {
      const tags = [
        item.horizon ? `<span class="tag"><b>Horizon</b> ${typeset(item.horizon)}</span>` : '',
        item.owner ? `<span class="tag"><b>Owner</b> ${typeset(item.owner)}</span>` : '',
      ].filter(Boolean).join('');
      return `
          <li class="rec" data-motion-item>
            <p class="rec__index" aria-hidden="true">${i + 1}</p>
            <h3 class="rec__action">${typeset(item.action)}</h3>
            <p class="rec__rationale">${typeset(item.rationale)}</p>
            ${tags ? `<p class="rec__tags">${tags}</p>` : ''}
          </li>`;
    }).join('');
    return `
      <ol class="recs" data-motion="stagger-up">${items}
      </ol>`;
  },

  roadmap: (section) => {
    const phases = section.phases.map((phase) => {
      const outcomes = phase.outcomes
        .map((o) => `<li>${typeset(o)}</li>`).join('');
      return `
            <li class="phase">
              <p class="eyebrow phase__window">${typeset(phase.window)}</p>
              <h3 class="subhead">${typeset(phase.name)}</h3>
              <ul class="phase__outcomes">${outcomes}</ul>
            </li>`;
    }).join('');
    return `
      <div class="roadmap" data-motion="path-draw">
        <div class="roadmap__rail">
          <svg class="roadmap__path" viewBox="0 0 1000 48" preserveAspectRatio="none" aria-hidden="true" focusable="false">
            <path d="M4 40C160 40 180 8 340 8 500 8 520 40 680 40 840 40 860 12 996 12"/>
          </svg>
        </div>
        <ol class="roadmap__phases">${phases}
        </ol>
      </div>`;
  },

  quote: (section) => {
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
  },

  heatmap: (section) => {
    const cols = section.columns.length;
    const head = section.columns.map((c) => `<th scope="col">${typeset(c)}</th>`).join('');
    const body = section.rows.map((row) => {
      const cells = row.values.map((v) => `
              <td data-cell>
                <span class="cell">${meter(v, 5)}<span class="cell__value">${v}<span class="visually-hidden"> out of 5</span></span></span>
              </td>`).join('');
      const note = row.note
        ? `<p class="heatmap__note">${typeset(row.note)}</p>`
        : '';
      return `
            <tr>
              <th scope="row">${typeset(row.capability)}${note}</th>${cells}
            </tr>`;
    }).join('');
    const legend = HEATMAP_SCALE
      .map(([n, label]) => `<li>${meter(n, 5)}<span>${n} — ${label}</span></li>`)
      .join('');
    return `
      <div class="heatmap" data-motion="cell-sweep" data-motion-cols="${cols}">
        <div class="heatmap__scroll">
          <table>
            <caption class="visually-hidden">${typeset(section.title)}, rated 1 to 5</caption>
            <thead><tr><th scope="col">Capability</th>${head}</tr></thead>
            <tbody>${body}
            </tbody>
          </table>
        </div>
        <ul class="heatmap__legend">${legend}</ul>
      </div>`;
  },

  'next-steps': (section) => {
    const items = section.items.map((item, i) => `
          <li class="next-step" data-motion-item>
            <span class="next-step__index" aria-hidden="true">${i + 1}</span>
            <span>${typeset(item)}</span>
          </li>`).join('');
    return `
      <ol class="next-steps" data-motion="stagger-up">${items}
      </ol>`;
  },

  methodology: (section) => `
      <div class="methodology">
        <div class="prose">${renderProse(section.body)}</div>
      </div>`,
};

const HEATMAP_SCALE = [
  [1, 'Absent'],
  [2, 'Emerging'],
  [3, 'Established'],
  [4, 'Advanced'],
  [5, 'Leading'],
];

/**
 * A KPI value only counts up when it is genuinely a number. Anything else
 * ("2.4x", "Q3", "Most") renders plainly, and count-up never sees it.
 */
function toNumeric(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    const decimals = (String(value).split('.')[1] ?? '').length;
    return { value, decimals };
  }
  if (typeof value === 'string' && /^-?\d{1,3}(,\d{3})*(\.\d+)?$/.test(value.trim())) {
    const plain = value.trim().replace(/,/g, '');
    return { value: Number(plain), decimals: (plain.split('.')[1] ?? '').length };
  }
  return null;
}

/* ==========================================================================
   Archetype-injected chrome
   ========================================================================== */

export function renderCover(meta, ctx) {
  const surface = ctx.coverSurface;                 // 'blue' | 'white' | 'black'
  const lockup = ctx.clientLogoPath
    ? `<div class="lockup"><img src="${esc(ctx.clientLogoPath)}" alt="${esc(meta.client)}" data-client-asset></div>`
    : '';
  const subtitle = meta.subtitle
    ? `<p class="cover__subtitle">${typeset(meta.subtitle)}</p>`
    : '';
  const authors = (meta.authors ?? []).length
    ? `<div><dt>Prepared by</dt>${meta.authors.map((a) =>
        `<dd>${typeset(a.name)}${a.role ? `, ${typeset(a.role)}` : ''}</dd>`).join('')}</div>`
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

export function renderRail(entries) {
  if (!entries.length) return '';
  const links = entries
    .map((e) => `<a class="rail__link" href="#${esc(e.id)}">${typeset(e.label)}</a>`)
    .join('');
  return `
    <nav class="rail" data-motion="scroll-sync" aria-label="Contents">
      <div class="rail__track"><div class="rail__fill"></div></div>
      <div class="rail__nav">${links}</div>
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

/** Wrap an authored section in its chrome. */
export function renderSection(section, index, ctx) {
  const type = resolveSectionType(section.type);
  const component = COMPONENTS[type];
  if (!component) throw new Error(`internal: no component registered for \`${type}\``);

  const id = sectionId(section, index);
  const title = section.title ?? FALLBACK_TITLE[type];
  const eyebrow = EYEBROW[type];
  const titled = type !== 'quote';
  const head = titled
    ? `
        <div class="section__head">
          ${eyebrow ? `<p class="eyebrow">${typeset(eyebrow)}</p>` : ''}
          <h2 class="headline" id="${esc(id)}-title">${typeset(title)}</h2>
        </div>`
    : '';
  const labelling = titled
    ? `aria-labelledby="${esc(id)}-title"`
    : `aria-label="${esc(title)}"`;

  return `
    <section class="section surface-white" id="${esc(id)}" ${labelling}>
      <div class="section__inner">${head}${component(section, ctx)}
      </div>
    </section>`;
}
