/** Load a template-owned static example and compose structure previews. */

import { existsSync } from 'node:fs';
import path from 'node:path';

import { ContentError, parseContentFile } from './content.mjs';

const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

function readStaticExample(archetype, modules, skillRoot, problems) {
  const relativeFile = archetype.static_example;
  if (typeof relativeFile !== 'string' || !relativeFile.trim()) {
    problems.push(`${archetype.name}: archetype.json must declare static_example`);
    return null;
  }
  const templateDir = path.join(skillRoot, 'templates', archetype.name);
  const file = path.resolve(templateDir, relativeFile);
  if (file !== templateDir && !file.startsWith(`${templateDir}${path.sep}`)) {
    problems.push(`${archetype.name}: static_example must stay inside its template folder`);
    return null;
  }
  if (!existsSync(file)) {
    problems.push(`${archetype.name}: missing ${relativeFile}`);
    return null;
  }
  let example;
  try {
    example = parseContentFile(file);
  } catch (err) {
    problems.push(`${archetype.name}: ${relativeFile} is invalid (${err.message})`);
    return null;
  }
  if (!isObject(example)) {
    problems.push(`${archetype.name}: ${relativeFile} must be a mapping`);
    return null;
  }
  if (example.meta?.archetype !== archetype.name) {
    problems.push(`${archetype.name}: static example meta.archetype must be ${archetype.name}`);
  }
  if (!Array.isArray(example.sections)) {
    problems.push(`${archetype.name}: static example sections must be a list`);
    return example;
  }

  const authorableViews = new Map(modules.flatMap((module) =>
    module.output
      .filter((output) => output.type !== 'cover')
      .map((output) => [`${module.id}:${output.id}`, { module, output }])));
  const seenViews = new Map();
  for (const [index, section] of example.sections.entries()) {
    const where = `${archetype.name}.${relativeFile}.sections[${index}]`;
    if (!isObject(section)) {
      problems.push(`${where} must be a mapping`);
      continue;
    }
    if (section.type !== undefined) problems.push(`${where} must not declare type`);
    const key = `${section.module}:${section.view}`;
    if (!authorableViews.has(key)) problems.push(`${where} does not match a selected module view`);
    else seenViews.set(key, (seenViews.get(key) ?? 0) + 1);
  }
  for (const [key] of authorableViews) {
    if (!seenViews.has(key)) problems.push(`${archetype.name}: static example is missing ${key}`);
    else if (seenViews.get(key) > 1) problems.push(`${archetype.name}: static example repeats ${key}`);
  }
  return example;
}

export function composeStructurePreview(archetype, modules, skillRoot, { previewModule = null } = {}) {
  const problems = [];
  const example = readStaticExample(archetype, modules, skillRoot, problems);
  if (previewModule && !modules.some((module) => module.id === previewModule)) {
    problems.push(`preview module ${previewModule} is not selected by template ${archetype.name}`);
  }
  if (problems.length) throw new ContentError(problems.map((problem) => `static template example: ${problem}`));
  return example;
}
