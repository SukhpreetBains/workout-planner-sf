/** Load module-owned example source and compose structure previews. */

import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

import { ContentError } from './content.mjs';

const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

function readExample(module, skillRoot, problems) {
  const file = path.join(skillRoot, 'modules', module.id, 'example.json');
  if (!existsSync(file)) {
    problems.push(`${module.id}: missing example.json`);
    return null;
  }
  let example;
  try {
    example = JSON.parse(readFileSync(file, 'utf8'));
  } catch (err) {
    problems.push(`${module.id}: example.json is not valid JSON (${err.message})`);
    return null;
  }
  if (!isObject(example)) {
    problems.push(`${module.id}: example.json must be a mapping`);
    return null;
  }
  if (example.schema_version !== 1) problems.push(`${module.id}: example schema_version must be 1`);
  if (example.module !== module.id) problems.push(`${module.id}: example module must be ${module.id}`);
  if (!Array.isArray(example.sections)) {
    problems.push(`${module.id}: example sections must be a list`);
    return example;
  }

  const authorableViews = (module.default_output ?? module.output).filter((output) => output.type !== 'cover');
  const knownViews = new Set(authorableViews.map((output) => output.id));
  const seenViews = new Set();
  for (const [index, section] of example.sections.entries()) {
    const where = `${module.id}.example.sections[${index}]`;
    if (!isObject(section)) {
      problems.push(`${where} must be a mapping`);
      continue;
    }
    if (section.type !== undefined || section.module !== undefined) {
      problems.push(`${where} declares only a view and its example data`);
    }
    if (!knownViews.has(section.view)) problems.push(`${where}.view is not an authorable module view`);
    else if (seenViews.has(section.view)) problems.push(`${where}.view repeats ${section.view}`);
    else seenViews.add(section.view);
  }
  for (const output of authorableViews) {
    if (!seenViews.has(output.id)) problems.push(`${module.id}: example is missing view ${output.id}`);
  }
  if (module.output.some((output) => output.type === 'cover') && !isObject(example.cover)) {
    problems.push(`${module.id}: the module owns a cover view, so example.cover is required`);
  }
  return example;
}

export function composeStructurePreview(archetype, modules, skillRoot, { previewModule = null } = {}) {
  const problems = [];
  const examples = modules.map((module) => ({ module, example: readExample(module, skillRoot, problems) }));
  if (previewModule && !modules.some((module) => module.id === previewModule)) {
    problems.push(`preview module ${previewModule} is not selected by template ${archetype.name}`);
  }
  if (problems.length) throw new ContentError(problems.map((problem) => `module examples: ${problem}`));

  const coverOwner = examples.find(({ module }) => module.output.some((output) => output.type === 'cover'));
  const cover = coverOwner?.example.cover ?? {};
  const title = previewModule
    ? `${modules.find((module) => module.id === previewModule).title} module preview`
    : `${archetype.title} module preview`;
  return {
    meta: {
      archetype: archetype.name,
      client: cover.client ?? 'Fictional example organization',
      title,
      subtitle: previewModule
        ? 'An isolated example of every view owned by this module'
        : 'Every template module shown with fictional example content',
      date: cover.date ?? '2026-01-15',
      authors: cover.authors ?? [{ name: 'Example delivery team', role: 'Structure preview' }],
      classification: cover.classification ?? 'Internal draft',
      accent: cover.accent ?? 'cyan',
    },
    sections: examples.flatMap(({ module, example }) =>
      module.output.filter((output) => output.type !== 'cover').map((output) => ({ ...example.sections.find((section) => section.view === output.id), module: module.id }))),
  };
}
