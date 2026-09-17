/** Load a template-owned static example and compose structure previews. */

import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

import { ContentError, parseContentFile } from './content.mjs';
import { SHARED_DIR } from './assets.mjs';

const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

/** Resolve `relativeFile` against `baseDir`, refusing to escape it. */
function resolveExampleFile(baseDir, relativeFile, label, problems) {
  if (typeof relativeFile !== 'string' || !relativeFile.trim()) {
    problems.push(`${label} must declare a static example path`);
    return null;
  }
  const file = path.resolve(baseDir, relativeFile);
  if (file !== baseDir && !file.startsWith(`${baseDir}${path.sep}`)) {
    problems.push(`${label}: static example must stay inside ${baseDir}`);
    return null;
  }
  if (!existsSync(file)) {
    problems.push(`${label}: missing ${relativeFile}`);
    return null;
  }
  return file;
}

/**
 * Parse `file` as a static example and validate it against `modules`: every
 * non-cover authorable view selected by the template must appear exactly
 * once. Used identically for a template's own static example and for an
 * industry pack's full alternate example — an override is held to the same
 * completeness bar as the template's own file, not a partial patch.
 */
function readAndValidateExample(file, archetype, modules, label, problems) {
  let example;
  try {
    example = parseContentFile(file);
  } catch (err) {
    problems.push(`${label}: ${path.basename(file)} is invalid (${err.message})`);
    return null;
  }
  if (!isObject(example)) {
    problems.push(`${label}: static example must be a mapping`);
    return null;
  }
  if (example.meta?.archetype !== archetype.name) {
    problems.push(`${label}: static example meta.archetype must be ${archetype.name}`);
  }
  if (!Array.isArray(example.sections)) {
    problems.push(`${label}: static example sections must be a list`);
    return example;
  }

  const authorableViews = new Map(modules.flatMap((module) =>
    module.output
      .filter((output) => output.type !== 'cover')
      .map((output) => [`${module.id}:${output.id}`, { module, output }])));
  const seenViews = new Map();
  for (const [index, section] of example.sections.entries()) {
    const where = `${label}.sections[${index}]`;
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
    if (!seenViews.has(key)) problems.push(`${label}: static example is missing ${key}`);
    else if (seenViews.get(key) > 1) problems.push(`${label}: static example repeats ${key}`);
  }
  return example;
}

function readTemplateExample(archetype, modules, skillRoot, problems) {
  const templateDir = path.join(skillRoot, 'templates', archetype.name);
  const file = resolveExampleFile(templateDir, archetype.static_example, archetype.name, problems);
  if (!file) return null;
  return readAndValidateExample(file, archetype, modules, archetype.name, problems);
}

/**
 * Resolve `shared/industry/<industry>/manifest.json` and the template-name
 * entry under its `examples.static_examples`, then validate that file the
 * same way as a template's own static example. Returns null (with a problem
 * pushed) if the pack, the manifest field, or the file itself is missing —
 * an industry with no override for this template is a configuration
 * problem to report, not something to silently fall back from.
 */
function readIndustryExample(archetype, modules, industry, problems) {
  const label = `industry ${industry}`;
  const packDir = path.join(SHARED_DIR, 'industry', industry);
  const manifestFile = path.join(packDir, 'manifest.json');
  if (!existsSync(manifestFile)) {
    problems.push(`${label}: no such industry pack (expected ${manifestFile})`);
    return null;
  }
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(manifestFile, 'utf8'));
  } catch (err) {
    problems.push(`${label}: manifest.json is invalid (${err.message})`);
    return null;
  }
  const relativeFile = manifest.examples?.static_examples?.[archetype.name];
  if (!relativeFile) {
    problems.push(`${label}: has no static example override for template \`${archetype.name}\``);
    return null;
  }
  const file = resolveExampleFile(packDir, relativeFile, label, problems);
  if (!file) return null;
  return readAndValidateExample(file, archetype, modules, label, problems);
}

export function composeStructurePreview(archetype, modules, skillRoot, { previewModule = null, industry = null } = {}) {
  const problems = [];
  const example = industry
    ? readIndustryExample(archetype, modules, industry, problems)
    : readTemplateExample(archetype, modules, skillRoot, problems);
  if (previewModule && !modules.some((module) => module.id === previewModule)) {
    problems.push(`preview module ${previewModule} is not selected by template ${archetype.name}`);
  }
  if (problems.length) throw new ContentError(problems.map((problem) => `static template example: ${problem}`));
  return example;
}
