/**
 * Validate reusable module definitions and a resumable deliverable intake.
 * The intake records evidence and decisions. It is deliberately separate from
 * content.yaml, which remains the presentation contract.
 */

import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

import { ContentError, parseContentFile } from './content.mjs';

export const ANSWER_TYPES = [
  'text', 'date', 'list', 'person', 'people', 'decision', 'milestones',
  'owned-actions', 'schedule', 'risks', 'table',
];
export const ANSWER_STATUSES = [
  'answered', 'partial', 'conflicting', 'missing', 'deferred', 'not_applicable',
];
export const ANSWER_DISPOSITIONS = ['rendered', 'summarized', 'supporting'];
export const UNRESOLVED_STATUSES = new Set(['partial', 'conflicting', 'missing', 'deferred']);

const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const hasValue = (value) => value !== null && value !== undefined && value !== ''
  && (!Array.isArray(value) || value.length > 0);

function answerMatchesType(value, answerType) {
  if (['text', 'person', 'decision'].includes(answerType)) return typeof value === 'string';
  if (answerType === 'date') return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
  return Array.isArray(value) && value.length > 0
    && value.every((item) => typeof item === 'string' || isObject(item));
}

function readJson(file, problems) {
  try {
    return JSON.parse(readFileSync(file, 'utf8'));
  } catch (err) {
    problems.push(`${file}: ${err.code === 'ENOENT' ? 'file does not exist' : err.message}`);
    return null;
  }
}

function normalizeModuleEntry(entry) {
  if (typeof entry === 'string') return { id: entry };
  return entry;
}

export function loadTemplateModules(archetype, skillRoot) {
  const problems = [];
  const modulesRoot = path.join(skillRoot, 'templates', 'modules');
  const seenModules = new Set();
  const seenQuestions = new Set();
  const modules = [];

  for (const [index, rawEntry] of (archetype.modules ?? []).entries()) {
    const entry = normalizeModuleEntry(rawEntry);
    if (!isObject(entry) || typeof entry.id !== 'string' || !/^[a-z0-9-]+$/.test(entry.id)) {
      problems.push(`archetype.modules[${index}] must name a lowercase module id`);
      continue;
    }
    if (seenModules.has(entry.id)) {
      problems.push(`archetype.modules repeats module \`${entry.id}\``);
      continue;
    }
    seenModules.add(entry.id);

    const moduleDir = path.join(modulesRoot, entry.id);
    const file = path.join(moduleDir, 'module.json');
    const module = readJson(file, problems);
    if (!module) continue;
    if (module.schema_version !== 1) problems.push(`${entry.id}: schema_version must be 1`);
    if (module.id !== entry.id) problems.push(`${entry.id}: module id must match its filename`);
    if (typeof module.title !== 'string' || !module.title) problems.push(`${entry.id}: title is required`);
    if (!Array.isArray(module.questions) || module.questions.length === 0) {
      problems.push(`${entry.id}: questions must be a non-empty list`);
      continue;
    }

    const excluded = new Set(entry.exclude_questions ?? []);
    const selected = entry.include_questions ? new Set(entry.include_questions) : null;
    const promoted = new Set(entry.promote_to_required ?? []);
    const questions = [];
    for (const [questionIndex, question] of module.questions.entries()) {
      const where = `${entry.id}.questions[${questionIndex}]`;
      if (!isObject(question)) { problems.push(`${where} must be a mapping`); continue; }
      if (typeof question.id !== 'string' || !question.id.startsWith(`${entry.id}.`)) {
        problems.push(`${where}.id must start with \`${entry.id}.\``);
        continue;
      }
      if (seenQuestions.has(question.id)) problems.push(`duplicate question id \`${question.id}\``);
      seenQuestions.add(question.id);
      if (!['required', 'optional'].includes(question.tier)) problems.push(`${question.id}: tier must be required or optional`);
      if (typeof question.prompt !== 'string' || !question.prompt) problems.push(`${question.id}: prompt is required`);
      if (!ANSWER_TYPES.includes(question.answer_type)) problems.push(`${question.id}: unknown answer_type \`${question.answer_type}\``);
      if (typeof question.source_ref !== 'string' || !question.source_ref) problems.push(`${question.id}: source_ref is required`);
      if ((selected && !selected.has(question.id)) || excluded.has(question.id)) continue;
      questions.push({
        ...question,
        tier: promoted.has(question.id) ? 'required' : question.tier,
      });
    }
    for (const id of [...excluded, ...(selected ?? []), ...promoted]) {
      if (!module.questions.some((question) => question.id === id)) {
        problems.push(`archetype module \`${entry.id}\` references unknown question \`${id}\``);
      }
    }
    const rawOutput = entry.output ?? module.default_output ?? [];
    let output = [];
    if (!Array.isArray(rawOutput)) {
      problems.push(`${entry.id}: output must be a list`);
    } else {
      const selectedIds = new Set(questions.map((question) => question.id));
      const allowedTypes = new Set(['cover', ...(archetype.allowed_sections ?? [])]);
      const seenViews = new Set();
      for (const [mappingIndex, mapping] of rawOutput.entries()) {
        const where = `${entry.id}.output[${mappingIndex}]`;
        if (!isObject(mapping)) { problems.push(`${where} must be a mapping`); continue; }
        if (typeof mapping.id !== 'string' || !/^[a-z0-9-]+$/.test(mapping.id)) {
          problems.push(`${where}.id must be a lowercase view id`);
        } else if (seenViews.has(mapping.id)) {
          problems.push(`${where}.id repeats view \`${mapping.id}\``);
        } else seenViews.add(mapping.id);
        if (!allowedTypes.has(mapping.type)) {
          problems.push(`${where}.type references unavailable section type \`${mapping.type}\``);
        }
        const rendererMatch = typeof mapping.renderer === 'string'
          ? mapping.renderer.match(/^(.+\.mjs)#([a-z0-9-]+)$/)
          : null;
        let rendererFile = null;
        let rendererExport = null;
        if (!rendererMatch) {
          problems.push(`${where}.renderer must be a relative .mjs path plus a named view, such as ../shared/html.mjs#agenda`);
        } else {
          rendererFile = path.resolve(moduleDir, rendererMatch[1]);
          rendererExport = rendererMatch[2];
          const relative = path.relative(modulesRoot, rendererFile);
          if (path.isAbsolute(relative) || relative === '..' || relative.startsWith(`..${path.sep}`)) {
            problems.push(`${where}.renderer must stay inside templates/modules`);
          } else if (!existsSync(rendererFile)) {
            problems.push(`${where}.renderer file does not exist: ${rendererFile}`);
          }
        }
        if (!Array.isArray(mapping.uses) || mapping.uses.length === 0) {
          problems.push(`${where}.uses must be a non-empty list`);
        } else {
          for (const id of mapping.uses) {
            if (!selectedIds.has(id)) problems.push(`${where}.uses references unselected question \`${id}\``);
          }
        }
        output.push({ ...mapping, rendererFile, rendererExport });
      }
    }
    modules.push({
      ...module,
      questions,
      output,
      template_entry: entry,
    });
  }

  if (problems.length) throw new ContentError(problems.map((problem) => `template modules: ${problem}`));
  return modules;
}

export function resolveGuidedContent(raw, modules) {
  if (modules.length === 0) return raw;
  const problems = [];
  const byId = new Map(modules.map((module) => [module.id, module]));
  const sections = Array.isArray(raw?.sections) ? raw.sections.map((section, index) => {
    if (!isObject(section)) return section;
    const where = `sections[${index}]`;
    if (section.type !== undefined) {
      problems.push(`${where}: guided content uses \`module\` and \`view\`; remove authored \`type\``);
    }
    const module = byId.get(section.module);
    if (!module) {
      problems.push(`${where}: module must name a module selected by this template`);
      return section;
    }
    const output = module.output.find((candidate) => candidate.id === section.view);
    if (!output) {
      problems.push(`${where}: view must name one of ${module.output.map((candidate) => candidate.id).join(', ')}`);
      return section;
    }
    return { ...section, type: output.type };
  }) : raw?.sections;
  if (problems.length) throw new ContentError(problems);
  return { ...raw, sections };
}

export async function loadModuleRenderers(modules) {
  const problems = [];
  const loadedFiles = new Map();
  const renderers = new Map();
  for (const module of modules) {
    for (const output of module.output) {
      if (!output.rendererFile || !output.rendererExport) continue;
      try {
        if (!loadedFiles.has(output.rendererFile)) {
          loadedFiles.set(output.rendererFile, await import(pathToFileURL(output.rendererFile).href));
        }
        const namespace = loadedFiles.get(output.rendererFile);
        const renderer = namespace.RENDERERS?.[output.rendererExport] ?? namespace[output.rendererExport];
        if (typeof renderer !== 'function') {
          problems.push(`${module.id}.${output.id}: renderer export \`${output.rendererExport}\` is not a function`);
          continue;
        }
        renderers.set(`${module.id}:${output.id}`, renderer);
      } catch (err) {
        problems.push(`${module.id}.${output.id}: cannot load renderer: ${err.message}`);
      }
    }
  }
  if (problems.length) throw new ContentError(problems.map((problem) => `module renderers: ${problem}`));
  return renderers;
}

function answerMap(intake, problems) {
  if (intake.answers === undefined) return {};
  if (!isObject(intake.answers)) {
    problems.push('intake.answers must be a mapping keyed by question id');
    return {};
  }
  return intake.answers;
}

export function evaluateIntake(intake, archetype, modules) {
  const problems = [];
  if (!isObject(intake)) throw new ContentError('the intake file must be a mapping');
  if (intake.schema_version !== 1) problems.push('intake.schema_version must be 1');
  if (intake.template !== archetype.name) {
    problems.push(`intake.template must be \`${archetype.name}\``);
  }
  const buildStatus = intake.build_status ?? 'draft';
  if (!['draft', 'final'].includes(buildStatus)) problems.push('intake.build_status must be draft or final');
  if (!['pending', 'answer', 'skipped', 'complete'].includes(intake.optional_review ?? 'pending')) {
    problems.push('intake.optional_review must be pending, answer, skipped, or complete');
  }

  const answers = answerMap(intake, problems);
  const known = new Map(modules.flatMap((module) =>
    module.questions.map((question) => [question.id, { ...question, module_id: module.id, module_title: module.title }])));
  for (const id of Object.keys(answers)) {
    if (!known.has(id)) problems.push(`intake.answers contains unknown question \`${id}\``);
  }

  const evaluated = [];
  for (const question of known.values()) {
    const raw = answers[question.id] ?? { status: 'missing' };
    if (!isObject(raw)) {
      problems.push(`${question.id}: answer must be a mapping`);
      continue;
    }
    const status = raw.status ?? 'missing';
    if (!ANSWER_STATUSES.includes(status)) problems.push(`${question.id}: unknown status \`${status}\``);
    if (status === 'answered' && !hasValue(raw.answer)) problems.push(`${question.id}: answered status requires an answer`);
    else if (status === 'answered' && !answerMatchesType(raw.answer, question.answer_type)) {
      problems.push(`${question.id}: answer does not match declared type \`${question.answer_type}\``);
    }
    if (status === 'answered') {
      if (!['source', 'user', 'mixed'].includes(raw.answered_by)) {
        problems.push(`${question.id}: answered status requires answered_by to be source, user, or mixed`);
      }
      if (!ANSWER_DISPOSITIONS.includes(raw.disposition)) {
        problems.push(`${question.id}: answered status requires disposition to be rendered, summarized, or supporting`);
      }
      if (['source', 'mixed'].includes(raw.answered_by)
        && (!Array.isArray(raw.sources) || raw.sources.length === 0)) {
        problems.push(`${question.id}: source-backed answers require at least one source citation`);
      }
    }
    if (status === 'not_applicable') {
      if (raw.answered_by !== 'user') problems.push(`${question.id}: only the user may mark a question not applicable`);
      if (!hasValue(raw.reason)) problems.push(`${question.id}: not applicable requires a reason`);
    }
    if (raw.sources !== undefined && !Array.isArray(raw.sources)) problems.push(`${question.id}: sources must be a list`);
    evaluated.push({ ...question, ...raw, status });
  }

  const requiredGaps = evaluated.filter((item) => item.tier === 'required' && UNRESOLVED_STATUSES.has(item.status));
  const optionalGaps = evaluated.filter((item) => item.tier === 'optional' && UNRESOLVED_STATUSES.has(item.status));
  const overrideAt = intake.override?.required_gaps_confirmed_at;
  if (buildStatus === 'final' && requiredGaps.length > 0 && !overrideAt) {
    problems.push('a final build with required gaps needs override.required_gaps_confirmed_at after explicit user confirmation');
  }
  if (problems.length) throw new ContentError(problems.map((problem) => `intake: ${problem}`));

  return {
    raw: intake,
    buildStatus,
    answers: evaluated,
    requiredGaps,
    optionalGaps,
    overrideConfirmedAt: overrideAt ?? null,
  };
}

export function loadAndEvaluateIntake(intakePath, archetype, modules) {
  if (!intakePath || !existsSync(intakePath)) {
    throw new ContentError(`the \`${archetype.name}\` template requires a separate intake file. Pass --intake <path>`);
  }
  return evaluateIntake(parseContentFile(path.resolve(intakePath)), archetype, modules);
}

export function decorateContentWithGaps(doc, intake, modules) {
  if (!intake || intake.requiredGaps.length === 0) return doc;
  const sections = doc.sections.map((section) => ({ ...section }));
  const allItems = intake.requiredGaps.map((gap) => ({
    id: gap.id,
    module: gap.module_title,
    prompt: gap.prompt,
    status: gap.status,
  }));
  sections.unshift({
    type: 'gap-summary',
    title: 'Required information still open',
    items: allItems,
  });

  for (const module of modules) {
    const gaps = intake.requiredGaps.filter((gap) => gap.module_id === module.id);
    if (gaps.length === 0) continue;
    const target = sections.find((section) => section.module === module.id && section.type !== 'gap-summary');
    const openQuestions = gaps.map((gap) => ({ id: gap.id, prompt: gap.prompt, status: gap.status }));
    if (target) target._openQuestions = openQuestions;
    else sections.push({
      type: 'open-questions',
      title: module.title,
      module: module.id,
      items: openQuestions,
    });
  }
  return { ...doc, sections };
}

export const INCOMPLETE_CONSEQUENCES = [
  'The kickoff may omit information needed for alignment or decisions.',
  'Empty or visibly incomplete sections will reduce the usefulness of the microsite.',
  'Unsupported synthesis is more likely if later edits try to bridge evidence gaps.',
  'Ownership, timing, dependencies, or acceptance expectations may remain unclear.',
];
