/** Reproducible review render of the shared floating citation implementation. */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseContentFile } from '../../../plugins/ascent/skills/create-deliverables/scripts/lib/content.mjs';
import { build } from '../../../plugins/ascent/skills/create-deliverables/scripts/build.mjs';
import { validateBuild } from '../../../plugins/ascent/skills/create-deliverables/scripts/validate-brand.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../..');
const output = path.join(root, 'build/citations-implementation-preview');
mkdirSync(output, { recursive: true });
const content = parseContentFile(path.join(root, 'plugins/ascent/skills/create-deliverables/templates/project-kickoff/static-example.yaml'));
content.meta.classification = 'Internal mockup · Fictional example';
for (const copy of content.meta.copy ?? []) if (copy.key === 'hero-meta-span-3') copy.text = content.meta.classification;
const objective = content.sections.find(section => section.module === 'objectives-and-success');
const timeline = content.sections.find(section => section.module === 'timeline-roadmap');
const actions = content.sections.find(section => section.module === 'immediate-next-steps');
objective.citations = [{
  target: 'item-1', label: 'Contact deflection', value: '30% reduction in avoidable contacts',
  status: 'source', source_ref: 'Fictional fixture · success-measures.md · OBJ-001',
  source_document: 'success-measures.md', source_locator: 'OBJ-001',
  excerpt: 'Target a 30% reduction in avoidable contacts by resolving more issues in the digital journey before agent escalation.',
  note: 'Illustrative source text for UI review.',
}];
timeline.citations = timeline.phases.slice(0, 2).map((phase, index) => ({
  target: `item-${index + 1}`, label: phase.name, value: `${phase.start} to ${phase.end}`,
  status: 'source', source_ref: `Fictional fixture · delivery-schedule.md · REQ-00${index + 1}`,
  source_document: 'delivery-schedule.md', source_locator: `REQ-00${index + 1}`,
  excerpt: `${phase.name} is scheduled from ${phase.start} to ${phase.end}. ${phase.summary}`,
  note: 'Illustrative source text for UI review.',
}));
actions.citations = [
  { target: 'item-3', label: 'Test-data pattern', value: 'Updated target date', status: 'changed',
    source_ref: 'Fictional fixture · kickoff-notes.md · REQ-007',
    source_document: 'kickoff-notes.md', source_locator: 'REQ-007',
    excerpt: 'Jordan and Theo will resolve the test-data pattern by September 18.',
    note: 'The displayed date was edited after the source text was recorded. Confirm support before treating it as reviewed.' },
  { target: 'item-4', label: 'MVP boundary', value: 'Approval action', status: 'missing',
    note: 'No source or review record is attached to this illustrative action.' },
];
const contentFile = path.join(output, 'content.json');
writeFileSync(contentFile, `${JSON.stringify(content, null, 2)}\n`);
const full = await build(contentFile, { out: path.join(output, 'site'), structurePreview: true, bundle: true });
const isolated = await build(contentFile, { out: path.join(output, 'timeline-isolated'), structurePreview: true, previewModule: 'timeline-roadmap', bundle: true });
if (process.argv.includes('--update-example')) {
  // This PR preview stays standalone without copying bundled Slalom Sans fonts.
  const bundle = readFileSync(isolated.bundlePath, 'utf8');
  const example = bundle.replace(/@font-face\s*\{[^}]*\}/g, '')
    .replace('<head>', '<head>\n<!-- Internal UI example. Slalom Sans font data is omitted from this review copy. -->')
    .replace(/[ \t]+$/gm, '');
  writeFileSync(path.join(here, 'example-timeline.html'), example);
}
const baseline = parseContentFile(contentFile);
for (const section of baseline.sections) delete section.citations;
const baselineFile = path.join(output, 'baseline-content.json');
writeFileSync(baselineFile, `${JSON.stringify(baseline, null, 2)}\n`);
const uncited = await build(baselineFile, { out: path.join(output, 'baseline'), structurePreview: true });
const gate = validateBuild(full.outDir);
const baselineGate = validateBuild(uncited.outDir);
const originalErrors = new Set(baselineGate.errors.map(error => JSON.stringify(error)));
const introduced = gate.errors.filter(error => !originalErrors.has(JSON.stringify(error)));
writeFileSync(path.join(output, 'validation.json'), `${JSON.stringify({ baseline_errors: baselineGate.errors.length, cited_errors: gate.errors.length, introduced_errors: introduced, warnings: gate.warnings }, null, 2)}\n`);
console.log(`Full preview: ${full.outDir}/index.html`);
console.log(`Isolated timeline: ${isolated.outDir}/index.html`);
console.log(`Standalone previews: ${full.bundlePath}; ${isolated.bundlePath}`);
console.log(`Brand gate: ${gate.errors.length} errors; ${introduced.length} introduced by citations.`);
if (introduced.length) process.exitCode = 1;
