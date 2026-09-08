#!/usr/bin/env node
/** Validate a modular template intake without building the microsite. */

import process from 'node:process';

import { SKILL_ROOT } from './lib/assets.mjs';
import { ContentError } from './lib/content.mjs';
import { loadAndEvaluateIntake, loadTemplateModules } from './lib/intake.mjs';
import { Report, fatal } from './lib/report.mjs';
import { loadArchetype } from './build.mjs';

export function validateIntakeFile(templateName, intakePath) {
  const archetype = loadArchetype(templateName);
  const modules = loadTemplateModules(archetype, SKILL_ROOT);
  if (modules.length === 0) throw new ContentError(`template \`${templateName}\` has no reusable modules`);
  return { archetype, modules, intake: loadAndEvaluateIntake(intakePath, archetype, modules) };
}

function main() {
  const [templateName, intakePath] = process.argv.slice(2);
  if (!templateName || !intakePath) {
    console.error('Usage: node scripts/validate-intake.mjs <template-name> <intake.yaml|json>');
    process.exitCode = 1;
    return;
  }
  try {
    const result = validateIntakeFile(templateName, intakePath);
    const report = new Report(`Template intake: ${templateName}`, { summary: false });
    report.note(`${result.modules.length} reusable modules`);
    report.note(`${result.intake.answers.filter((answer) => answer.tier === 'required').length} required questions`);
    report.note(`${result.intake.answers.filter((answer) => answer.tier === 'optional').length} optional questions`);
    report.note(`${result.intake.requiredGaps.length} required gaps`);
    report.note(`${result.intake.optionalGaps.length} optional gaps`);
    report.print();

    for (const module of [...result.modules, {id: result.archetype.name, title: `${result.archetype.title} preferences`}]) {
      const gaps = result.intake.requiredGaps.filter((gap) => gap.module_id === module.id);
      if (!gaps.length) continue;
      console.log(`  ${module.title} (${gaps.length})`);
      for (const gap of gaps) console.log(`    - ${gap.prompt} [${gap.status}]`);
    }
    if (result.intake.requiredGaps.length) console.log('');
  } catch (err) {
    if (err instanceof ContentError) return fatal(err);
    throw err;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) main();
