/**
 * content.mjs — parse and schema-validate a deliverable's content file.
 *
 * The microsite is a pure function of this content. Every rule here fails
 * loudly: a typo that silently drops a finding from a client readout is worse
 * than a build that refuses to run.
 */

import { readFileSync } from 'node:fs';
import path from 'node:path';
import { parseYaml, YamlError } from './yaml.mjs';

export class ContentError extends Error {
  constructor(problems) {
    const list = Array.isArray(problems) ? problems : [problems];
    super(`content is not valid:\n  - ${list.join('\n  - ')}`);
    this.name = 'ContentError';
    this.problems = list;
  }
}

export const ACCENTS = ['cyan', 'coral-red', 'purple', 'chartreuse'];
export const SEVERITIES = ['high', 'medium', 'low'];

const META_FIELDS = {
  archetype: { type: 'string', required: true },
  client: { type: 'string', required: true },
  title: { type: 'string', required: true },
  subtitle: { type: 'string' },
  date: { type: 'string', required: true, pattern: /^\d{4}-\d{2}-\d{2}$/, hint: 'ISO 8601, e.g. 2026-08-11' },
  authors: { type: 'list', of: { name: { type: 'string', required: true }, role: { type: 'string' } } },
  classification: { type: 'string', required: true },
  accent: { type: 'string', required: true, enum: ACCENTS },
  client_logo: { type: 'string' },
};

/**
 * The authorable section types. `cover`, `progress-rail` and `footer` are
 * injected by the archetype and are deliberately not authorable.
 */
export const SECTION_SCHEMA = {
  'exec-summary': {
    title: { type: 'string' },
    body: { type: 'prose', required: true },
  },
  purpose: {
    title: { type: 'string' },
    body: { type: 'prose', required: true },
  },
  'kpi-row': {
    title: { type: 'string' },
    items: {
      type: 'list', required: true, min: 2, max: 4,
      maxHint: 'a KPI row past four tiles breaks both the layout and comprehension',
      of: {
        value: { type: 'scalar', required: true },
        unit: { type: 'string' },
        label: { type: 'string', required: true },
        source: { type: 'string', required: true, hint: 'an unsourced number in a client deliverable is a liability' },
      },
    },
  },
  'theme-group': {
    title: { type: 'string', required: true },
    body: { type: 'prose' },
    findings: {
      type: 'list', required: true, min: 1,
      of: {
        theme: { type: 'string', required: true },
        evidence: { type: 'string', required: true },
        implication: {
          type: 'string', required: true,
          hint: 'theme + evidence without a so-what is not a finding; the implication is what makes a readout defensible',
        },
        severity: { type: 'string', enum: SEVERITIES },
        icon: { type: 'icon' },
      },
    },
  },
  recommendations: {
    title: { type: 'string' },
    items: {
      type: 'list', required: true, min: 1,
      of: {
        action: { type: 'string', required: true },
        rationale: { type: 'string', required: true },
        horizon: { type: 'string' },
        owner: { type: 'string' },
      },
    },
  },
  roadmap: {
    title: { type: 'string' },
    time_scale: { type: 'string', enum: ['auto', 'week', 'two-week', 'month'] },
    phases: {
      type: 'list', required: true, min: 1, max: 6,
      maxHint: 'timeline components support one to six scannable phases',
      of: {
        name: { type: 'string', required: true },
        window: { type: 'string', required: true },
        start: { type: 'string', pattern: /^\d{4}-\d{2}-\d{2}$/, hint: 'ISO 8601, e.g. 2026-08-11' },
        end: { type: 'string', pattern: /^\d{4}-\d{2}-\d{2}$/, hint: 'ISO 8601, e.g. 2026-08-11' },
        summary: { type: 'string' },
        outcomes: { type: 'stringlist', required: true, min: 1 },
        activities: {
          type: 'list', max: 6,
          of: {
            title: { type: 'string', required: true },
            detail: { type: 'string' },
          },
        },
        decision: { type: 'string' },
        milestones: {
          type: 'list', max: 4,
          of: {
            title: { type: 'string', required: true },
            date: { type: 'string', pattern: /^\d{4}-\d{2}-\d{2}$/, hint: 'ISO 8601, e.g. 2026-08-11' },
            detail: { type: 'string' },
          },
        },
      },
    },
  },
  quote: {
    quote: { type: 'string', required: true },
    name: { type: 'string', required: true },
    attribution_title: { type: 'string' },
  },
  heatmap: {
    title: { type: 'string', required: true },
    columns: { type: 'stringlist', required: true, min: 1, max: 4 },
    rows: {
      type: 'list', required: true, min: 1,
      of: {
        capability: { type: 'string', required: true },
        values: { type: 'numberlist', required: true, min: 1, range: [1, 5] },
        note: { type: 'string' },
      },
    },
  },
  'next-steps': {
    title: { type: 'string' },
    items: { type: 'stringlist', required: true, min: 1 },
  },
  methodology: {
    title: { type: 'string' },
    body: { type: 'prose', required: true },
  },
  agenda: {
    title: { type: 'string' },
    items: {
      type: 'list', required: true, min: 1,
      of: {
        title: { type: 'string', required: true },
        detail: { type: 'prose', required: true },
      },
    },
  },
  table: {
    title: { type: 'string', required: true },
    columns: { type: 'stringlist', required: true, min: 1 },
    rows: {
      type: 'list', required: true, min: 1,
      of: {
        cells: { type: 'stringlist', required: true, min: 1 },
      },
    },
  },
};

/** `timeline` and `roadmap` are the same section under two names. */
export const SECTION_ALIASES = { timeline: 'roadmap' };

export function resolveSectionType(type) {
  return SECTION_ALIASES[type] ?? type;
}

export function validSectionTypes() {
  return [...Object.keys(SECTION_SCHEMA), ...Object.keys(SECTION_ALIASES)].sort();
}

const isPlainObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

function checkFields(value, fields, where, problems, ctx) {
  if (!isPlainObject(value)) {
    problems.push(`${where}: expected a mapping of fields, found ${describe(value)}`);
    return;
  }
  for (const key of Object.keys(value)) {
    if (!(key in fields)) {
      problems.push(`${where}: unknown key \`${key}\` (valid keys: ${Object.keys(fields).join(', ')})`);
    }
  }
  for (const [key, spec] of Object.entries(fields)) {
    const present = key in value && value[key] !== null && value[key] !== '';
    if (!present) {
      if (spec.required) {
        problems.push(`${where}: missing required field \`${key}\`${spec.hint ? ` — ${spec.hint}` : ''}`);
      }
      continue;
    }
    checkValue(value[key], spec, `${where}.${key}`, problems, ctx);
  }
}

function checkValue(v, spec, where, problems, ctx) {
  switch (spec.type) {
    case 'string':
      if (typeof v !== 'string') { problems.push(`${where}: expected text, found ${describe(v)}`); return; }
      if (spec.pattern && !spec.pattern.test(v)) {
        problems.push(`${where}: \`${v}\` is not valid${spec.hint ? ` — ${spec.hint}` : ''}`);
      }
      if (spec.enum && !spec.enum.includes(v)) {
        problems.push(`${where}: \`${v}\` is not one of ${spec.enum.join(', ')}`);
      }
      break;

    case 'scalar':
      if (typeof v !== 'string' && typeof v !== 'number') {
        problems.push(`${where}: expected text or a number, found ${describe(v)}`);
      }
      break;

    case 'prose':
      if (typeof v !== 'string') { problems.push(`${where}: expected text, found ${describe(v)}`); return; }
      checkProse(v, where, problems);
      break;

    case 'icon':
      if (typeof v !== 'string') { problems.push(`${where}: expected an icon name, found ${describe(v)}`); return; }
      if (ctx.iconNames && !ctx.iconNames.has(v)) {
        problems.push(`${where}: \`${v}\` is not an approved icon. Pick one from the active branding pack's assets/iconography/ (never draw a new one).`);
      }
      break;

    case 'stringlist':
    case 'numberlist':
    case 'list': {
      if (!Array.isArray(v)) { problems.push(`${where}: expected a list, found ${describe(v)}`); return; }
      if (spec.min !== undefined && v.length < spec.min) {
        problems.push(`${where}: needs at least ${spec.min} item${spec.min === 1 ? '' : 's'}, found ${v.length}`);
      }
      if (spec.max !== undefined && v.length > spec.max) {
        problems.push(`${where}: at most ${spec.max} items, found ${v.length}${spec.maxHint ? ` — ${spec.maxHint}` : ''}`);
      }
      v.forEach((item, i) => {
        const at = `${where}[${i}]`;
        if (spec.type === 'stringlist') {
          if (typeof item !== 'string' && typeof item !== 'number') {
            problems.push(`${at}: expected text, found ${describe(item)}`);
          }
        } else if (spec.type === 'numberlist') {
          if (typeof item !== 'number' || !Number.isFinite(item)) {
            problems.push(`${at}: expected a number, found ${describe(item)}`);
          } else if (spec.range && (item < spec.range[0] || item > spec.range[1])) {
            problems.push(`${at}: ${item} is outside ${spec.range[0]}–${spec.range[1]}`);
          }
        } else {
          checkFields(item, spec.of, at, problems, ctx);
        }
      });
      break;
    }

    default:
      throw new Error(`internal: unknown field type \`${spec.type}\``);
  }
}

/**
 * Prose is a markdown subset. An external link would break the "zero external
 * references" delivery rule, so it is refused at authoring time rather than
 * discovered by the validator after the build.
 */
function checkProse(text, where, problems) {
  const external = text.match(/\]\(\s*(https?:\/\/[^)]+)\)/i) ?? text.match(/(https?:\/\/\S+)/i);
  if (external) {
    problems.push(`${where}: contains an external link (${external[1]}). A client deliverable must make no external requests — quote the source in text instead.`);
  }
}

function describe(v) {
  if (v === null || v === undefined) return 'nothing';
  if (Array.isArray(v)) return 'a list';
  if (typeof v === 'object') return 'a mapping';
  return `${typeof v} \`${v}\``;
}

/**
 * Validate a parsed content document against the schema and, when supplied,
 * an archetype manifest. Throws ContentError listing every problem at once.
 */
export function validateContent(doc, { archetype = null, iconNames = null } = {}) {
  const problems = [];
  const ctx = { iconNames };

  if (!isPlainObject(doc)) throw new ContentError(`the content file must be a mapping with \`meta\` and \`sections\` keys, found ${describe(doc)}`);

  for (const key of Object.keys(doc)) {
    if (key !== 'meta' && key !== 'sections') {
      problems.push(`unknown top-level key \`${key}\` (valid keys: meta, sections)`);
    }
  }

  if (!('meta' in doc)) problems.push('missing required key `meta`');
  else checkFields(doc.meta, META_FIELDS, 'meta', problems, ctx);

  if (!('sections' in doc) || !Array.isArray(doc.sections)) {
    problems.push('missing required key `sections` (a list of sections)');
  } else if (doc.sections.length === 0) {
    problems.push('`sections` is empty — there is nothing to render');
  } else {
    const seen = [];
    doc.sections.forEach((section, i) => {
      const where = `sections[${i}]`;
      if (!isPlainObject(section)) { problems.push(`${where}: expected a mapping, found ${describe(section)}`); return; }
      const rawType = section.type;
      if (typeof rawType !== 'string' || rawType === '') {
        problems.push(`${where}: missing required field \`type\` (valid types: ${validSectionTypes().join(', ')})`);
        return;
      }
      const type = resolveSectionType(rawType);
      const schema = SECTION_SCHEMA[type];
      if (!schema) {
        problems.push(`${where}: unknown section type \`${rawType}\` (valid types: ${validSectionTypes().join(', ')})`);
        return;
      }
      seen.push(rawType);
      if (archetype) {
        const allowed = archetype.allowed_sections ?? [];
        if (!allowed.includes(rawType) && !allowed.includes(type)) {
          problems.push(`${where}: the \`${archetype.name}\` archetype does not permit a \`${rawType}\` section (it allows: ${allowed.join(', ')})`);
        }
      }
      checkFields(section, {
        type: { type: 'string', required: true },
        module: { type: 'string' },
        view: { type: 'string' },
        ...schema,
      }, where, problems, ctx);
      if (type === 'roadmap' && Array.isArray(section.phases)) {
        section.phases.forEach((phase, phaseIndex) => {
          if (!isPlainObject(phase)) return;
          const phaseWhere = `${where}.phases[${phaseIndex}]`;
          const hasStart = typeof phase.start === 'string' && phase.start !== '';
          const hasEnd = typeof phase.end === 'string' && phase.end !== '';
          if (hasStart !== hasEnd) {
            problems.push(`${phaseWhere}: start and end must be supplied together; execution_map never invents the missing boundary`);
          } else if (hasStart && /^\d{4}-\d{2}-\d{2}$/.test(phase.start) && /^\d{4}-\d{2}-\d{2}$/.test(phase.end)
              && phase.end < phase.start) {
            problems.push(`${phaseWhere}: end must be on or after start`);
          }
        });
      }
    });

    if (archetype?.required_sections?.length) {
      for (const required of archetype.required_sections) {
        if (!seen.some((t) => resolveSectionType(t) === resolveSectionType(required))) {
          problems.push(`the \`${archetype.name}\` archetype requires a \`${required}\` section`);
        }
      }
    }
  }

  if (archetype && isPlainObject(doc.meta) && typeof doc.meta.archetype === 'string'
      && doc.meta.archetype !== archetype.name) {
    problems.push(`meta.archetype is \`${doc.meta.archetype}\` but the loaded archetype is \`${archetype.name}\``);
  }

  if (problems.length) throw new ContentError(problems);
  return doc;
}

/** Read and parse a `.yaml` / `.yml` / `.json` content file. */
export function parseContentFile(filePath) {
  let text;
  try {
    text = readFileSync(filePath, 'utf8');
  } catch (err) {
    throw new ContentError(`cannot read the content file \`${filePath}\` (${err.code ?? err.message})`);
  }
  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.json') {
    try {
      return JSON.parse(text);
    } catch (err) {
      throw new ContentError(`\`${filePath}\` is not valid JSON: ${err.message}`);
    }
  }
  if (ext === '.yaml' || ext === '.yml') {
    try {
      return parseYaml(text);
    } catch (err) {
      if (err instanceof YamlError) {
        throw new ContentError(`\`${filePath}\` ${err.message}`);
      }
      throw err;
    }
  }
  throw new ContentError(`unsupported content format \`${ext || filePath}\` — use .yaml, .yml, or .json`);
}

/** Parse + validate in one step. */
export function loadContent(filePath, options = {}) {
  return validateContent(parseContentFile(filePath), options);
}
