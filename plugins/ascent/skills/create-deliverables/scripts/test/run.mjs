#!/usr/bin/env node
/**
 * run.mjs — the whole test suite. Zero dependencies.
 *
 *   node scripts/test/run.mjs [name-filter]
 *
 * Four blocks:
 *   1. the YAML subset parser, including every construct it must refuse
 *   2. content schema validation
 *   3. an end-to-end build of the worked example, plus --bundle
 *   4. the validator: a clean build passes, and every rule is proved to catch
 *      a deliberately broken build. A validator that has never failed is not
 *      known to work.
 */

import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import process from 'node:process';

import { parseYaml, YamlError } from '../lib/yaml.mjs';
import { ContentError, validateContent } from '../lib/content.mjs';
import { SKILL_ROOT, listIconNames } from '../lib/assets.mjs';
import { build, buildStructurePreview, loadArchetype } from '../build.mjs';
import { evaluateIntake, loadTemplateModules, resolveGuidedContent } from '../lib/intake.mjs';
import {
  addQuestionFollowUp, collectEvidenceCandidates, createEvidenceDelegationPlan,
  createQuestionLedger, formatNumberedQuestion, questionNumberMapping, validateEvidenceExtractionResult,
} from '../lib/intake-orchestration.mjs';
import { detachBuild } from '../detach.mjs';
import { rebuildDetached } from '../rebuild-detached.mjs';
import { validateBuild } from '../validate-brand.mjs';
import { writeBundle } from '../lib/bundle.mjs';
import { style } from '../lib/report.mjs';
import { registerDeliveryTests } from './delivery.mjs';

/* ==========================================================================
   Runner
   ========================================================================== */

const tests = [];
const only = process.argv[2] ?? '';
const test = (name, fn) => tests.push({ name, fn });

class Failure extends Error {}

function ok(condition, message) {
  if (!condition) throw new Failure(message ?? 'expected a truthy value');
}

function eq(actual, expected, message) {
  const a = JSON.stringify(actual);
  const b = JSON.stringify(expected);
  if (a !== b) throw new Failure(`${message ?? 'not equal'}\n      expected ${b}\n      actual   ${a}`);
}

function includes(haystack, needle, message) {
  if (!String(haystack).includes(needle)) {
    throw new Failure(`${message ?? 'missing text'}\n      expected to contain ${JSON.stringify(needle)}\n      in ${JSON.stringify(String(haystack).slice(0, 300))}`);
  }
}

/** Assert that `fn` throws, and return the error for further assertions. */
function throws(fn, message) {
  try {
    fn();
  } catch (err) {
    return err;
  }
  throw new Failure(message ?? 'expected this to throw, and it did not');
}

/* ==========================================================================
   1. YAML subset parser
   ========================================================================== */

test('yaml: nested mappings, sequences and scalar types', () => {
  const doc = parseYaml([
    'meta:',
    '  client: Northwind Health',
    '  count: 12',
    '  ratio: 2.4',
    '  flag: true',
    '  missing: null',
    '  quoted: "a: colon # and a hash"',
    "  single: 'it''s fine'",
    'sections:',
    '  - type: kpi-row',
    '    items:',
    '      - value: 34',
    '        unit: "%"',
    '  - type: next-steps',
    '    items: [one, "two, still two", 3]',
    '',
  ].join('\n'));

  eq(doc.meta.client, 'Northwind Health');
  eq(doc.meta.count, 12);
  eq(doc.meta.ratio, 2.4);
  eq(doc.meta.flag, true);
  eq(doc.meta.missing, null);
  eq(doc.meta.quoted, 'a: colon # and a hash');
  eq(doc.meta.single, "it's fine");
  eq(doc.sections[0].items[0], { value: 34, unit: '%' });
  eq(doc.sections[1].items, ['one', 'two, still two', 3]);
});

test('yaml: comments and blank lines are ignored', () => {
  eq(parseYaml('# leading\n\na: 1   # trailing\n\n# trailing comment\n'), { a: 1 });
});

test('yaml: literal block scalar keeps newlines, indentation and hashes', () => {
  const doc = parseYaml('body: |\n  One.\n    indented\n\n  After a blank. # kept\n');
  eq(doc.body, 'One.\n  indented\n\nAfter a blank. # kept\n');
});

test('yaml: folded block scalar joins lines and honours the strip indicator', () => {
  eq(parseYaml('a: >\n  one\n  two\n\n  three\n').a, 'one two\nthree\n');
  eq(parseYaml('a: >-\n  one\n  two\n').a, 'one two');
  eq(parseYaml('a: |-\n  one\n  two\n').a, 'one\ntwo');
});

test('yaml: a URL scalar survives the missing-space-after-colon check', () => {
  eq(parseYaml('a:\n  - https://example.com/x\n'), { a: ['https://example.com/x'] });
});

const REFUSALS = {
  'anchors (&)': 'a: &x 1\nb: 2\n',
  'aliases (*)': 'a: 1\nb: *x\n',
  'document markers': '---\na: 1\n',
  'tags (!!)': 'a: !!str 1\n',
  'complex keys (?)': '? a\n: b\n',
  'flow mappings ({})': 'a: {b: 1}\n',
  'tab indentation': 'a:\n\tb: 1\n',
  'odd indentation': 'a:\n   b: 1\n',
  'a key with no colon': 'a: 1\nb\n',
  'a colon with no space': 'a:1\n',
  'a duplicate key': 'a: 1\na: 2\n',
  'an unterminated quote': 'a: "oops\n',
  'an inline value plus a block': 'a: 1\n  b: 2\n',
  'an empty block scalar': 'a: |\nb: 2\n',
  'a sequence item where a key belongs': 'a: 1\n- b\n',
  'a nested inline sequence': 'a:\n  - - b\n',
  'a keep indicator (+)': 'a: |+\n  b\n',
  'a document not starting at column 0': '  a: 1\n',
};

for (const [label, source] of Object.entries(REFUSALS)) {
  test(`yaml: refuses ${label} with a line number`, () => {
    const err = throws(() => parseYaml(source), `${label} was accepted, which risks a silent mis-parse`);
    ok(err instanceof YamlError, `expected a YamlError, got ${err.name}: ${err.message}`);
    ok(/^line \d+: /.test(err.message), `error should name a line: ${err.message}`);
  });
}

/* ==========================================================================
   2. Content validation
   ========================================================================== */

const ARCHETYPE = loadArchetype('project-kickoff');
const ICONS = listIconNames();

function content(overrides = {}) {
  const base = {
    meta: {
      archetype: 'project-kickoff',
      client: 'Test Client',
      title: 'A minimal kickoff',
      date: '2026-01-15',
      classification: 'Internal draft',
      accent: 'cyan',
    },
    sections: [
      { type: 'purpose', module: 'objectives-and-scope', body: 'One paragraph.' },
      { type: 'agenda', module: 'kickoff-context', items: [{ title: 'One topic', detail: 'What the topic covers.' }] },
      { type: 'table', module: 'team-and-responsibilities', title: 'Team', columns: ['Name'], rows: [{ cells: ['One person'] }] },
      { type: 'roadmap', module: 'delivery-approach', phases: [{ name: 'Learn', window: 'Week 1', outcomes: ['One outcome'] }] },
      {
        type: 'theme-group',
        module: 'raid',
        title: 'What we heard',
        findings: [{ theme: 'T', evidence: 'E', implication: 'I' }],
      },
      { type: 'next-steps', module: 'immediate-next-steps', items: ['One'] },
    ],
  };
  return { ...structuredClone(base), ...overrides };
}

const check = (doc) => validateContent(doc, { archetype: ARCHETYPE, iconNames: ICONS });

function contentError(doc, needle) {
  const err = throws(() => check(doc), `expected a ContentError mentioning ${JSON.stringify(needle)}`);
  ok(err instanceof ContentError, `expected a ContentError, got ${err.name}: ${err.message}`);
  includes(err.message, needle);
  return err;
}

test('content: the worked minimal example validates', () => {
  ok(check(content()));
});

test('content: a missing required meta field names the field', () => {
  const doc = content();
  delete doc.meta.classification;
  contentError(doc, 'meta: missing required field `classification`');
});

test('content: an unknown meta key is an error, not a silent drop', () => {
  const doc = content();
  doc.meta.acccent = 'cyan';
  contentError(doc, 'unknown key `acccent`');
});

test('content: an unknown top-level key is an error', () => {
  const doc = content();
  doc.setions = [];
  contentError(doc, 'unknown top-level key `setions`');
});

test('content: an accent outside the four secondaries is an error', () => {
  const doc = content();
  doc.meta.accent = 'teal';
  contentError(doc, 'meta.accent: `teal` is not one of cyan, coral-red, purple, chartreuse');
});

test('content: a non-ISO date is an error', () => {
  const doc = content();
  doc.meta.date = '15/01/2026';
  contentError(doc, 'ISO 8601');
});

test('content: an unknown section type lists the valid types', () => {
  const doc = content();
  doc.sections.push({ type: 'testimonials' });
  const err = contentError(doc, 'unknown section type `testimonials`');
  includes(err.message, 'theme-group');
});

test('content: a section the archetype forbids is an error', () => {
  const narrow = { ...ARCHETYPE, allowed_sections: ['purpose'] };
  const err = throws(() => validateContent(content(), { archetype: narrow, iconNames: ICONS }));
  includes(err.message, 'does not permit a `agenda` section');
});

test('content: a required section the archetype demands is an error when absent', () => {
  const doc = content();
  doc.sections = doc.sections.filter((s) => s.type !== 'next-steps');
  contentError(doc, 'requires a `next-steps` section');
});

test('content: a kpi-row over four items is an error', () => {
  const doc = content();
  doc.sections.push({
    type: 'kpi-row',
    items: Array.from({ length: 5 }, (_, i) => ({ value: i, label: 'L', source: 'S' })),
  });
  contentError(doc, 'at most 4 items, found 5');
});

test('content: a kpi-row under two items is an error', () => {
  const doc = content();
  doc.sections.push({ type: 'kpi-row', items: [{ value: 1, label: 'L', source: 'S' }] });
  contentError(doc, 'needs at least 2 items');
});

test('content: an unsourced KPI is an error', () => {
  const doc = content();
  doc.sections.push({
    type: 'kpi-row',
    items: [{ value: 1, label: 'L' }, { value: 2, label: 'L2', source: 'S' }],
  });
  contentError(doc, 'liability');
});

test('content: a finding without an implication is an error', () => {
  const doc = content();
  delete doc.sections[4].findings[0].implication;
  contentError(doc, 'missing required field `implication`');
});

test('content: an unapproved icon is an error', () => {
  const doc = content();
  doc.sections[4].findings[0].icon = 'sparkle-magic';
  contentError(doc, 'is not an approved icon');
});

test('content: a severity outside high/medium/low is an error', () => {
  const doc = content();
  doc.sections[4].findings[0].severity = 'critical';
  contentError(doc, '`critical` is not one of high, medium, low');
});

test('content: heatmap values outside 1-5 are an error', () => {
  const doc = content();
  doc.sections.push({
    type: 'heatmap', title: 'H', columns: ['Now'],
    rows: [{ capability: 'C', values: [7] }],
  });
  contentError(doc, 'is outside 1–5');
});

test('content: an external link in prose is an error', () => {
  const doc = content();
  doc.sections[0].body = 'See [the source](https://example.com/report).';
  contentError(doc, 'must make no external requests');
});

test('content: every problem is reported at once, not one at a time', () => {
  const doc = content();
  delete doc.meta.client;
  delete doc.meta.title;
  doc.meta.accent = 'teal';
  const err = throws(() => check(doc));
  ok(err.problems.length >= 3, `expected at least 3 problems, got ${err.problems.length}`);
});

test('content: meta.archetype must match the loaded archetype', () => {
  const doc = content();
  doc.meta.archetype = 'something-else';
  contentError(doc, 'but the loaded archetype is');
});

/* ==========================================================================
   3. Build
   ========================================================================== */

const TMP = path.join(os.tmpdir(), 'create-deliverables-tests');
rmSync(TMP, { recursive: true, force: true });
mkdirSync(TMP, { recursive: true });

const EXAMPLE = path.join(SKILL_ROOT, 'templates', 'project-kickoff', 'content.example.yaml');
const FIXTURES = path.join(SKILL_ROOT, 'scripts', 'test', 'fixtures');
const MODULES = loadTemplateModules(ARCHETYPE, SKILL_ROOT);

function writeIntake(name, { missing = [], buildStatus = 'draft', confirmAt = null } = {}) {
  const missingIds = new Set(missing);
  const answers = {};
  for (const module of MODULES) {
    for (const question of module.questions) {
      answers[question.id] = question.tier === 'optional' || missingIds.has(question.id)
        ? { status: 'missing' }
        : {
          status: 'answered',
          answer: question.answer_type === 'date'
            ? '2026-03-02'
            : ['text', 'person', 'decision'].includes(question.answer_type)
              ? 'Covered by the fictional project-kickoff example.'
              : ['Covered by the fictional project-kickoff example.'],
          answered_by: 'source',
          disposition: 'rendered',
          sources: [{ source_id: 'fictional-example', locator: 'templates/project-kickoff/content.example.yaml' }],
        };
    }
  }
  const file = path.join(TMP, `${name}.json`);
  writeFileSync(file, JSON.stringify({
    schema_version: 1,
    template: 'project-kickoff',
    build_status: buildStatus,
    optional_review: 'skipped',
    answers,
    ...(confirmAt ? { override: { required_gaps_confirmed_at: confirmAt } } : {}),
  }));
  return file;
}

const COMPLETE_INTAKE = writeIntake('complete-intake');
const INCOMPLETE_INTAKE = writeIntake('incomplete-intake', { missing: ['ways-of-working.status-source'] });

let example = null;   // the reference build, shared by the validator tests

test('modules: project-kickoff has eight reusable modules and the expected question tiers', () => {
  eq(MODULES.length, 8);
  eq(MODULES.flatMap((module) => module.questions).filter((question) => question.tier === 'required').length, 67);
  eq(MODULES.flatMap((module) => module.questions).filter((question) => question.tier === 'optional').length, 56);
});

test('modules: sibling folders own their definitions and finished renderers', () => {
  ok(!existsSync(path.join(SKILL_ROOT, 'templates', 'modules')), 'modules must be a sibling of templates');
  const shared = readFileSync(path.join(SKILL_ROOT, 'modules', 'shared', 'primitives.mjs'), 'utf8');
  ok(!shared.includes('RENDERERS'), 'shared primitives must not register finished module views');
  for (const module of MODULES) {
    const moduleDir = path.join(SKILL_ROOT, 'modules', module.id);
    ok(existsSync(path.join(moduleDir, 'module.json')));
    ok(existsSync(path.join(moduleDir, 'html.mjs')));
    for (const output of module.output) {
      eq(output.rendererFile, path.join(moduleDir, 'html.mjs'));
      ok(existsSync(output.rendererFile), `missing renderer for ${module.id}.${output.id}`);
    }
  }
});

test('modules: every module has renderable example source', async () => {
  for (const module of MODULES) {
    ok(existsSync(path.join(SKILL_ROOT, 'modules', module.id, 'example.json')));
  }
  const result = await buildStructurePreview({
    moduleId: 'objectives-and-scope',
    out: path.join(TMP, 'objectives-and-scope-example'),
  });
  eq(result.renderedDoc.sections.map((section) => section.view), ['purpose', 'success-measures', 'scope-details']);
  includes(result.html, 'data-preview-module="objectives-and-scope"');
  includes(result.html, `Module: ${MODULES.find((module) => module.id === 'objectives-and-scope').title}`);
});

test('templates: the example preview renders every selected module with labels', async () => {
  const result = await buildStructurePreview({
    templateName: 'project-kickoff',
    out: path.join(TMP, 'project-kickoff-module-examples'),
  });
  const renderedModules = new Set(result.renderedDoc.sections.map((section) => section.module));
  eq([...renderedModules], MODULES.map((module) => module.id));
  for (const module of MODULES) {
    includes(result.html, `data-preview-module="${module.id}"`);
  }
});

test('modules: guided content requires module plus view and derives section type', () => {
  const raw = JSON.parse(readFileSync(path.join(FIXTURES, 'valid-minimal.json'), 'utf8'));
  const resolved = resolveGuidedContent(raw, MODULES);
  eq(resolved.sections[0].type, 'purpose');
  const invalid = structuredClone(raw);
  invalid.sections[0].type = 'purpose';
  const err = throws(() => resolveGuidedContent(invalid, MODULES));
  includes(err.message, 'remove authored `type`');
});

test('review-backed intake: skill uses current rows and closes document bypasses', () => {
  const skill = readFileSync(path.join(SKILL_ROOT, 'SKILL.md'), 'utf8');
  includes(skill, 'workspace/.system/tracker-copies/<category>.yaml');
  includes(skill, 'stable row ID');
  includes(skill, 'Do not search `sources.yaml`');
  includes(skill, 'deliverable-only document bypass');
  includes(skill, 'Module or question count alone is');
  ok(!skill.includes('Search both evidence stores'));
  ok(!skill.includes('or use them only for this'));
});

test('guided workflow: template and module selections are explicit', () => {
  const skill = readFileSync(path.join(SKILL_ROOT, 'SKILL.md'), 'utf8');
  includes(skill, 'complete template catalog');
  includes(skill, 'Ask the user to explicitly select one template');
  includes(skill, 'Never default\nto `project-kickoff`');
  includes(skill, 'complete ordered list of modules associated with that template');
  includes(skill, 'confirm that selection before\nevidence intake');
  ok(!skill.includes('`project-kickoff` when no other template is selected'));
});

test('draft intake: requested drafts render before the gap interview', () => {
  const skill = readFileSync(path.join(SKILL_ROOT, 'SKILL.md'), 'utf8');
  includes(skill, 'Do not block on a gap');
  includes(skill, 'Omit unsupported fields, rows, and views');
  includes(skill, 'Show the resulting draft to the user before offering to resolve the gaps.');
  includes(skill, 'Final builds retain');
});

test('intake: only a user can mark a question not applicable', () => {
  const raw = JSON.parse(readFileSync(COMPLETE_INTAKE, 'utf8'));
  raw.answers['kickoff-context.audience'] = { status: 'not_applicable', answered_by: 'source', reason: 'No audience.' };
  const err = throws(() => evaluateIntake(raw, ARCHETYPE, MODULES));
  includes(err.message, 'only the user may mark a question not applicable');
});

test('intake: a final build with gaps requires explicit confirmation', () => {
  const raw = JSON.parse(readFileSync(INCOMPLETE_INTAKE, 'utf8'));
  raw.build_status = 'final';
  const err = throws(() => evaluateIntake(raw, ARCHETYPE, MODULES));
  includes(err.message, 'needs override.required_gaps_confirmed_at');
});

test('intake: every answered item records its content disposition', () => {
  const raw = JSON.parse(readFileSync(COMPLETE_INTAKE, 'utf8'));
  delete raw.answers['kickoff-context.audience'].disposition;
  const err = throws(() => evaluateIntake(raw, ARCHETYPE, MODULES));
  includes(err.message, 'requires disposition to be rendered, summarized, or supporting');
});

test('intake: source-backed answers include a citation', () => {
  const raw = JSON.parse(readFileSync(COMPLETE_INTAKE, 'utf8'));
  delete raw.answers['kickoff-context.audience'].sources;
  const err = throws(() => evaluateIntake(raw, ARCHETYPE, MODULES));
  includes(err.message, 'source-backed answers require at least one source citation');
});

test('intake orchestration: module and source counts do not trigger delegation', () => {
  const fixture = JSON.parse(readFileSync(path.join(FIXTURES, 'five-module-evidence.json'), 'utf8'));
  const selected = MODULES.filter((module) => fixture.selected_module_ids.includes(module.id));
  const plan = createEvidenceDelegationPlan({ selectedModules: selected, approvedEvidenceFiles: fixture.evidence_files });
  ok(!plan.delegate);
  ok(plan.questionCount >= 20);
  eq(plan.assignments, []);
});

test('intake orchestration: explicitly substantial mapping can delegate in parallel', () => {
  const fixture = JSON.parse(readFileSync(path.join(FIXTURES, 'five-module-evidence.json'), 'utf8'));
  const selected = MODULES.filter((module) => fixture.selected_module_ids.includes(module.id));
  const plan = createEvidenceDelegationPlan({ selectedModules: selected, approvedEvidenceFiles: fixture.evidence_files, manuallyAssembledIntake: true });
  ok(plan.delegate);
  eq(plan.assignments.length, 5);
  eq(plan.model, 'gpt-5.6-luna');
  eq(plan.reasoning, 'high');
  eq(plan.assignments[0].selected_module_ids, ['kickoff-context']);
  ok(plan.assignments[0].canonical_questions.every((question) => question.id.startsWith('kickoff-context.')));
  includes(plan.assignments[0].safety, 'Use only the supplied current tracker rows');
});

test('intake orchestration: structured extraction rejects unsupported sources and preserves conflicts for reconciliation', () => {
  const module = MODULES.find((item) => item.id === 'kickoff-context');
  const plan = createEvidenceDelegationPlan({ selectedModules: [module, MODULES[1], MODULES[2]], approvedEvidenceFiles: [{ source_id: 'charter', path: 'charter.md' }], manuallyAssembledIntake: true });
  const assignment = plan.assignments[0];
  const valid = validateEvidenceExtractionResult(assignment, { findings: [{
    question_id: 'kickoff-context.project-name', status: 'conflicting', citations: [{ source_id: 'charter', locator: 'line 4' }], explanation: 'The charter and agenda use different names.',
  }] });
  eq(valid[0].status, 'conflicting');
  const candidates = collectEvidenceCandidates([valid, [{ ...valid[0], explanation: 'A second reviewer found the same conflict.' }]]);
  eq(candidates.get('kickoff-context.project-name').length, 2);
  const err = throws(() => validateEvidenceExtractionResult(assignment, { findings: [{
    question_id: 'kickoff-context.project-name', status: 'answered', answer: 'Northwind', citations: [{ source_id: 'unknown', locator: 'line 4' }],
  }] }));
  includes(err.message, 'citation source is not approved');
});

test('intake orchestration: unavailable subagents fall back to the primary agent', () => {
  const plan = createEvidenceDelegationPlan({ selectedModules: MODULES.slice(0, 3), approvedEvidenceFiles: [{ source_id: 'a', path: 'a.md' }], manuallyAssembledIntake: true, subagentsAvailable: false });
  ok(!plan.delegate);
  eq(plan.fallback, 'primary-agent sequential evidence pass');
});

test('intake questions: numbering is sequential, multipart, and stable through follow-ups', () => {
  const decisionRights = MODULES.find((module) => module.id === 'team-and-responsibilities')
    .questions.find((question) => question.id.endsWith('.decision-rights'));
  const ledger = createQuestionLedger([
    { id: 'kickoff-context.project-name', prompt: 'What is the project name?' },
    decisionRights,
    { id: 'delivery-approach.methodology', prompt: 'What approach will be used?' },
  ]);
  const displayed = formatNumberedQuestion(decisionRights, ledger, 3);
  includes(displayed, 'Question 2 of 3\n\n2. Who has final decision authority for each area?\n2.1 Scope');
  includes(displayed, '2.5 Acceptance');
  eq(addQuestionFollowUp(ledger, decisionRights.id), '2a');
  includes(formatNumberedQuestion(decisionRights, ledger, 3, '2a'), 'Question 2a of 3');
  eq(ledger.numbers.get('delivery-approach.methodology'), '3');
  eq(questionNumberMapping(ledger), {
    'kickoff-context.project-name': '1',
    'team-and-responsibilities.decision-rights': '2',
    'delivery-approach.methodology': '3',
  });
  const raw = JSON.parse(readFileSync(COMPLETE_INTAKE, 'utf8'));
  raw.display_question_numbers = questionNumberMapping(ledger);
  ok(evaluateIntake(raw, ARCHETYPE, MODULES));
});

test('build: the worked project-kickoff example builds end to end', async () => {
  example = await build(EXAMPLE, { out: path.join(TMP, 'example'), bundle: true, intake: COMPLETE_INTAKE });
  ok(existsSync(path.join(example.outDir, 'index.html')));
  eq(example.manifest.archetype, 'project-kickoff');
  eq(example.manifest.accent, 'cyan');
  eq(example.manifest.required_question_count, 67);
});

test('build: the output folder has the expected structure', () => {
  for (const rel of [
    'index.html', 'service-cloud-discovery-core-team-kickoff.html', 'brand-manifest.json',
    'css/tokens.css', 'css/base.css', 'css/components.css', 'css/print.css',
    'js/motion.js', 'js/anime.esm.min.js', 'js/LICENSE.md',
    'assets/logo-slalom-white.svg',
  ]) {
    ok(existsSync(path.join(example.outDir, rel)), `missing ${rel}`);
  }
});

test('build: data-accent is set on <html> from meta.accent', () => {
  includes(example.html, 'data-accent="cyan" data-deliverable-status="draft"');
});

test('build: every data-motion value has a recipe in motion.js', () => {
  const motion = readFileSync(path.join(example.outDir, 'js/motion.js'), 'utf8');
  const recipes = new Set([...motion.matchAll(/^ {2}'?([a-z-]+)'?:\s*\(/gm)].map((m) => m[1]));
  ok(recipes.size >= 8, `expected at least 8 recipes, parsed ${recipes.size} — has the format changed?`);
  const declared = new Set([...example.html.matchAll(/data-motion="([a-z-]+)"/g)].map((m) => m[1]));
  ok(declared.size > 0, 'the build declared no motion at all');
  for (const name of declared) ok(recipes.has(name), `no recipe for data-motion="${name}"`);
});

test('build: fonts are copied to flat, space-free paths', () => {
  for (const weight of ['light', 'regular', 'bold', 'black']) {
    for (const ext of ['woff2', 'woff']) {
      ok(existsSync(path.join(example.outDir, 'fonts', `slalom-sans-${weight}.${ext}`)),
        `missing fonts/slalom-sans-${weight}.${ext}`);
    }
  }
  const css = readFileSync(path.join(example.outDir, 'css/base.css'), 'utf8');
  ok(!css.includes('%20'), 'the CSS points at a path containing an escaped space');
  ok(!/Webfont Files/.test(css), 'the CSS points at the source directory name');
});

test('build: no .otf is ever shipped', () => {
  const stack = [example.outDir];
  while (stack.length) {
    const dir = stack.pop();
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) stack.push(full);
      else ok(!entry.name.endsWith('.otf'), `shipped a desktop font: ${full}`);
    }
  }
});

test('build: icons referenced by findings are copied, unreferenced ones are not', () => {
  eq(example.manifest.icons.sort(), ['people', 'search']);
  ok(!existsSync(path.join(example.outDir, 'assets/icon-coffee.svg')));
});

test('build: a JSON content file is a first-class input', async () => {
  const result = await build(path.join(FIXTURES, 'valid-minimal.json'), { out: path.join(TMP, 'json'), intake: COMPLETE_INTAKE });
  includes(result.html, 'A minimal kickoff');
  eq(result.manifest.accent, 'chartreuse');
});

test('build: the long-content layout stress fixture builds', async () => {
  const result = await build(path.join(FIXTURES, 'layout-stress.json'), { out: path.join(TMP, 'layout-stress'), intake: COMPLETE_INTAKE });
  includes(result.html, 'A deliberately long KPI value');
  includes(result.html, 'A deliberately long table value designed to exercise wrapping');
});

test('build: the project-kickoff worked example passes the gate', async () => {
  const examplePath = path.join(SKILL_ROOT, 'templates', 'project-kickoff', 'content.example.yaml');
  const result = await build(examplePath, { out: path.join(TMP, 'kickoff'), intake: COMPLETE_INTAKE });
  eq(result.manifest.archetype, 'project-kickoff');
  ok(existsSync(path.join(result.outDir, 'index.html')));
  includes(result.html, 'class="agenda"');
  includes(result.html, 'class="data-table"');
  const report = validateBuild(result.outDir);
  eq(report.errors.length, 0, `unexpected errors: ${report.errors.map((e) => e.message).join('; ')}`);
});

test('build: one module can render in isolation with its normal renderer paths', async () => {
  const result = await build(EXAMPLE, {
    out: path.join(TMP, 'kickoff-context-isolated'),
    intake: COMPLETE_INTAKE,
    previewModule: 'kickoff-context',
  });
  eq(result.manifest.preview_module, 'kickoff-context');
  eq(result.renderedDoc.sections.map((section) => section.view), ['agenda', 'working-agreement']);
  includes(result.html, 'class="agenda"');
  includes(result.html, '<details class="agenda-item__disclosure"');
  includes(result.html, 'Meet the people responsible for the engagement');
  const agendaGroups = [...result.html.matchAll(/name="(agenda-[^"]+)"/g)].map((match) => match[1]);
  ok(agendaGroups.length > 1, 'expected multiple clickable agenda items');
  ok(agendaGroups.every((name) => name === agendaGroups[0]), 'agenda items must share one exclusive disclosure group');
  ok(!result.html.includes('Core team &amp; roles'), 'another module leaked into the isolated preview');
});

test('layout: components keep content visible and constrain data-driven columns', () => {
  const baseCss = readFileSync(path.join(SKILL_ROOT, 'assets', 'css', 'base.css'), 'utf8');
  const componentsCss = readFileSync(path.join(SKILL_ROOT, 'assets', 'css', 'components.css'), 'utf8');
  ok(!/overflow-x:\s*hidden/.test(baseCss), 'page-level horizontal overflow must not hide layout failures');
  includes(componentsCss, 'container-type: inline-size;', 'KPI tiles need container-aware typography');
  includes(componentsCss, 'minmax(10rem, 18rem)', 'recommendation metadata needs a bounded column');
  includes(componentsCss, 'overflow-wrap: anywhere;', 'long client-provided content must be able to wrap');
});

test('build: the minimal YAML fixture and its JSON twin render identically', async () => {
  const y = await build(path.join(FIXTURES, 'valid-minimal.yaml'), { out: path.join(TMP, 'yaml'), intake: COMPLETE_INTAKE });
  const j = await build(path.join(FIXTURES, 'valid-minimal.json'), { out: path.join(TMP, 'json2'), intake: COMPLETE_INTAKE });
  eq(y.html, j.html, 'the YAML and JSON inputs produced different HTML');
});

test('build: an unknown archetype fails with an actionable message', () => {
  const err = throws(() => loadArchetype('no-such-archetype'));
  includes(err.message, 'no archetype named `no-such-archetype`');
  includes(err.message, 'references/archetypes.md');
});

test('build: a non-numeric KPI value degrades to a plain render', () => {
  includes(example.html, '1 in 5');
  const tile = example.html.slice(example.html.indexOf('1 in 5') - 400, example.html.indexOf('1 in 5'));
  ok(!/data-count-to/.test(tile.slice(-120)), 'a non-numeric KPI was given a count-up target');
  includes(example.html, 'data-count-to="6"');
});

test('build: content is escaped, not injected', async () => {
  const doc = JSON.parse(readFileSync(path.join(FIXTURES, 'valid-minimal.json'), 'utf8'));
  doc.meta.client = '<script>alert(1)</script>';
  writeFileSync(path.join(TMP, 'xss.json'), JSON.stringify(doc));
  const result = await build(path.join(TMP, 'xss.json'), { out: path.join(TMP, 'xss'), intake: COMPLETE_INTAKE });
  ok(!result.html.includes('<script>alert(1)</script>'), 'unescaped content reached the output');
  includes(result.html, '&lt;script&gt;');
});

test('build: incomplete drafts show only a compact notice above the content', async () => {
  const result = await build(EXAMPLE, { out: path.join(TMP, 'incomplete'), intake: INCOMPLETE_INTAKE });
  includes(result.html, 'Draft: 1 required question is unanswered.');
  eq((result.html.match(/class="draft-notice /g) ?? []).length, 1);
  ok(result.html.indexOf('class="draft-notice ') < result.html.indexOf('<main'));
  ok(!result.html.includes('What is the authoritative source for project status?'));
  ok(!result.html.includes('This section is incomplete'));
  ok(!result.html.includes('class="gap-summary"'));
  ok(!result.html.includes('class="open-questions"'));
  eq(result.manifest.unresolved_required_questions, ['ways-of-working.status-source']);
});

test('build: incomplete drafts do not create sections for missing module content', async () => {
  const intake = writeIntake('sparse-draft-intake', {
    missing: ['ways-of-working.status-source', 'kickoff-context.project-name'],
  });
  const result = await build(path.join(FIXTURES, 'valid-minimal.json'), {
    out: path.join(TMP, 'sparse-draft'), intake,
  });
  const complete = await build(path.join(FIXTURES, 'valid-minimal.json'), {
    out: path.join(TMP, 'sparse-complete'), intake: COMPLETE_INTAKE,
  });
  includes(result.html, 'Draft: 2 required questions are unanswered.');
  eq(result.html.match(/<main id="main">([\s\S]*?)<\/main>/)[1],
    complete.html.match(/<main id="main">([\s\S]*?)<\/main>/)[1]);
  ok(!complete.html.includes('class="draft-notice '));
  eq(result.manifest.unresolved_required_questions.length, 2);
});

test('build: an explicitly confirmed final build may retain required gaps', async () => {
  const intake = writeIntake('confirmed-final-intake', {
    missing: ['ways-of-working.status-source'],
    buildStatus: 'final',
    confirmAt: '2026-09-02T12:00:00Z',
  });
  const result = await build(EXAMPLE, { out: path.join(TMP, 'confirmed-final'), intake });
  eq(result.manifest.build_status, 'final');
  includes(result.html, 'What is the authoritative source for project status?');
  ok(!result.html.includes('class="draft-notice '));
});

test('detach: incomplete builds require confirmation and rebuild from local source', async () => {
  const built = await build(EXAMPLE, { out: path.join(TMP, 'detach-source'), intake: INCOMPLETE_INTAKE });
  const packageDir = path.join(TMP, 'detached-package');
  const err = throws(() => detachBuild(built.outDir, packageDir));
  includes(err.message, '--confirm-incomplete');
  const detached = detachBuild(built.outDir, packageDir, { confirmIncomplete: true });
  ok(existsSync(path.join(detached.sourceDir, 'index.html')));
  eq(detached.manifest.mode, 'detached');
  const rebuilt = rebuildDetached(packageDir);
  eq(rebuilt.gate.errors.length, 0);
});

/* ==========================================================================
   4. --bundle
   ========================================================================== */

test('bundle: the single file has no external reference and stands alone', () => {
  eq(example.manifest.bundle_filename, 'service-cloud-discovery-core-team-kickoff.html');
  const bundle = readFileSync(path.join(example.outDir, example.manifest.bundle_filename), 'utf8');
  ok(!existsSync(path.join(example.outDir, 'bundle.html')), 'legacy bundle.html should not be emitted');
  ok(!/<link\b[^>]*stylesheet/i.test(bundle), 'standalone HTML still links a stylesheet');
  ok(!/<script\b[^>]*\ssrc=/i.test(bundle), 'standalone HTML still loads a script by src');
  ok(!/\ssrc="assets\//.test(bundle), 'standalone HTML still references an image file');
  ok(!/(?:src|href)="\s*(?:https?:)?\/\//i.test(bundle), 'standalone HTML makes an external reference');
  includes(bundle, '"animejs":"data:text/javascript;base64,');
  includes(bundle, 'url("data:font/woff2;base64,');
  ok(!/format\("woff"\)/.test(bundle), 'the bundle should carry woff2 only');
});

test('bundle: refuses to inline a motion layer containing a closing script tag', () => {
  const dir = path.join(TMP, 'bad-bundle');
  cpSync(example.outDir, dir, { recursive: true });
  const js = path.join(dir, 'js/motion.js');
  writeFileSync(js, `${readFileSync(js, 'utf8')}\n// </script>\n`);
  const err = throws(() => writeBundle(dir));
  includes(err.message, 'closing script tag');
});

/* ==========================================================================
   5. The validator — a clean build passes, and every rule catches a break
   ========================================================================== */

test('validator: a clean build passes with zero errors', () => {
  const report = validateBuild(example.outDir);
  eq(report.errors.map((e) => `${e.rule}: ${e.message}`), [], 'a clean build reported errors');
  ok(report.checks > 100, `expected a substantial number of checks, ran ${report.checks}`);
});

test('validator: the clean build warns about the shipped Slalom Sans files', () => {
  const report = validateBuild(example.outDir);
  const warn = report.warnings.find((w) => w.rule === 'rule 28');
  ok(warn, 'rule 28 did not warn about shipping the font files');
  includes(warn.message, 'redistribution');
});

test('validator: the clean build discloses the known brand deviations', () => {
  const report = validateBuild(example.outDir);
  const deviations = report.warnings.filter((w) => w.rule === 'deviation');
  ok(deviations.length >= 2, `expected the serif and Slalom line deviations, got ${deviations.length}`);
});

/** Patch helpers used by the broken fixtures below. */
const patch = (dir, rel, fn) => {
  const full = path.join(dir, rel);
  writeFileSync(full, fn(readFileSync(full, 'utf8')));
};
const replace = (dir, rel, from, to) => patch(dir, rel, (text) => {
  if (!text.includes(from)) throw new Failure(`fixture setup: \`${from}\` not found in ${rel}`);
  return text.replace(from, to);
});
const append = (dir, rel, text) => patch(dir, rel, (old) => old + text);

/**
 * Copy the clean build, break it, and assert the named rule catches it.
 * `expect` may be a rule label or `{ rule, warn: true }`.
 */
function brokenFixture(name, expect, breakIt) {
  const wantWarn = typeof expect === 'object' && expect.warn === true;
  const label = typeof expect === 'object' ? expect.rule : expect;
  test(`validator: ${label} catches ${name}`, () => {
    const dir = path.join(TMP, `broken-${label.replace(/\s+/g, '')}-${slug(name)}`);
    rmSync(dir, { recursive: true, force: true });
    cpSync(example.outDir, dir, { recursive: true });
    breakIt(dir);
    const report = validateBuild(dir);
    const found = (wantWarn ? report.warnings : report.errors).filter((e) => e.rule === label);
    ok(found.length > 0,
      `${label} did not ${wantWarn ? 'warn' : 'fail'}. Errors: ${
        report.errors.map((e) => e.rule).join(', ') || 'none'}. Warnings: ${
        report.warnings.map((e) => e.rule).join(', ') || 'none'}`);
  });
}

const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30).replace(/-$/, '');

// --- Palette and composition ------------------------------------------------

brokenFixture('a hex literal outside tokens.css', 'rule 1', (dir) =>
  append(dir, 'css/components.css', '\n.smuggled { color: #FF0000; }\n'));

brokenFixture('an rgb() literal outside tokens.css', 'rule 1', (dir) =>
  append(dir, 'css/components.css', '\n.smuggled { color: rgb(255 0 0); }\n'));

brokenFixture('an off-palette colour in tokens.css', 'rule 2', (dir) =>
  append(dir, 'css/tokens.css', '\n:root { --rogue: #123456; }\n'));

brokenFixture('data-accent disagreeing with the content', 'rule 3', (dir) =>
  replace(dir, 'index.html', 'data-accent="cyan"', 'data-accent="purple"'));

brokenFixture('a component naming a secondary colour directly', 'rule 3', (dir) =>
  append(dir, 'css/components.css', '\n.finding { border-color: var(--chartreuse); }\n'));

brokenFixture('a composition with no Slalom Blue', 'rule 4', (dir) =>
  patch(dir, 'css/tokens.css', (css) =>
    css.replace(/#0C62FB/g, '#000000').replace(/#002FAF/g, '#000000')));

brokenFixture('a second colour bar', 'rule 5', (dir) =>
  replace(dir, 'index.html', '<div class="color-bar"', '<div class="color-bar"></div><div class="color-bar"'));

brokenFixture('a reordered colour bar', 'rule 5', (dir) =>
  replace(dir, 'index.html',
    '<span class="color-bar__swatch color-bar__swatch--cyan"></span><span class="color-bar__swatch color-bar__swatch--coral-red"></span>',
    '<span class="color-bar__swatch color-bar__swatch--coral-red"></span><span class="color-bar__swatch color-bar__swatch--cyan"></span>'));

brokenFixture('a colour bar taller than 20% of the layout', 'rule 5', (dir) =>
  replace(dir, 'css/components.css', 'max-height: 20%;', 'max-height: 45%;'));

brokenFixture('a background-matching swatch not moved to Dark 3', 'rule 6', (dir) =>
  replace(dir, 'css/components.css',
    '[data-bar-bg="blue"] .color-bar__swatch--blue { background: var(--slalom-dark-blue); }',
    '[data-bar-bg="blue"] .color-bar__swatch--blue { background: var(--cyan); }'));

brokenFixture('a swatch override that changes more than the background', 'rule 6', (dir) =>
  replace(dir, 'css/components.css',
    '[data-bar-bg="blue"] .color-bar__swatch--blue { background: var(--slalom-dark-blue); }',
    '[data-bar-bg="blue"] .color-bar__swatch--blue { background: var(--slalom-dark-blue); flex: 2; }'));

brokenFixture('a decorative gradient', 'rule 7', (dir) =>
  append(dir, 'css/components.css', '\n.cover { background-image: linear-gradient(var(--slalom-blue), var(--white)); }\n'));

// --- Typography -------------------------------------------------------------

brokenFixture('a font stack that does not start with Slalom Sans', 'rule 8', (dir) =>
  replace(dir, 'css/tokens.css', '--font-sans: "Slalom Sans"', '--font-sans: Helvetica, "Slalom Sans"'));

brokenFixture('a missing font-synthesis: none', 'rule 8', (dir) =>
  replace(dir, 'css/base.css', 'font-synthesis: none;', 'font-weight: normal;'));

brokenFixture('a weight Slalom Sans does not have', 'rule 8', (dir) =>
  append(dir, 'css/components.css', '\n.finding__title { font-weight: 500; }\n'));

brokenFixture('an @font-face declaring an unshipped weight', 'rule 8', (dir) =>
  append(dir, 'css/base.css',
    '\n@font-face { font-family: "Slalom Sans"; src: url("../fonts/slalom-sans-bold.woff2") format("woff2"), url("../fonts/slalom-sans-bold.woff") format("woff"); font-weight: 600; font-style: normal; }\n'));

brokenFixture('Avenir leaking into web output', 'rule 9', (dir) =>
  append(dir, 'css/components.css', '\n.display { font-family: "Avenir Next LT Pro", sans-serif; }\n'));

brokenFixture('a headline set in capitals', 'rule 10', (dir) =>
  replace(dir, 'index.html', '>Risks &amp; open questions</h2>', '>RISKS &amp; OPEN QUESTIONS</h2>'));

brokenFixture('all caps outside an eyebrow label', 'rule 10', (dir) =>
  append(dir, 'css/components.css', '\n.rec__action { text-transform: uppercase; }\n'));

brokenFixture('justified type', 'rule 11', (dir) =>
  append(dir, 'css/components.css', '\n.prose { text-align: justify; }\n'));

brokenFixture('centred body copy', 'rule 11', (dir) =>
  append(dir, 'css/components.css', '\n.rec__rationale { text-align: center; }\n'));

brokenFixture('a fifth type size in a composition', { rule: 'rule 12', warn: true }, (dir) =>
  append(dir, 'css/components.css', '\n.finding__implication { font-size: 1.2rem; }\n'));

// --- Assets -----------------------------------------------------------------

brokenFixture('a recoloured logo', 'rule 13', (dir) =>
  patch(dir, 'assets/logo-slalom-white.svg', (svg) => svg.replace(/fill="#FFFFFF"|#FFFFFF/gi, '#FF00FF')));

brokenFixture('a logo below the 9px minimum', 'rule 14', (dir) =>
  replace(dir, 'css/tokens.css', '--logo-height: 2rem;', '--logo-height: 6px;'));

brokenFixture('clear space narrower than an "o"', 'rule 14', (dir) =>
  replace(dir, 'css/tokens.css', 'calc(var(--logo-height) * 0.45)', 'calc(var(--logo-height) * 0.1)'));

brokenFixture('an icon that is not from the approved library', 'rule 15', (dir) =>
  writeFileSync(path.join(dir, 'assets/icon-people.svg'),
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'));

brokenFixture('an icon reversed onto a dark surface', 'rule 16', (dir) =>
  replace(dir, 'index.html',
    '<section class="section surface-white" id="s7-risks-open-questions"',
    '<section class="section surface-black" id="s7-risks-open-questions"'));

brokenFixture('an icon on a Slalom Blue circle', 'rule 16', (dir) => {
  append(dir, 'css/components.css', '\n.blue-disc { border-radius: 50%; background: var(--slalom-blue); } /* no-text */\n');
  replace(dir, 'index.html', '<div class="finding__title">', '<div class="finding__title blue-disc">');
});

// --- Accessibility ----------------------------------------------------------

brokenFixture('an unapproved text-on-background pair', 'rule 17', (dir) =>
  append(dir, 'css/components.css',
    '\n.invented { background: var(--surface-white-bg); color: var(--on-blue-body); }\n'));

brokenFixture('a background with no paired text colour', 'rule 17', (dir) =>
  append(dir, 'css/components.css', '\n.orphan { background: var(--surface-black-bg); padding: 1rem; }\n'));

brokenFixture('a colour set outside the surface contract', 'rule 17', (dir) =>
  append(dir, 'css/components.css', '\n.freelance { color: var(--chartreuse-light-3); }\n'));

brokenFixture('a text colour below 4.5:1', 'rule 18', (dir) =>
  replace(dir, 'css/tokens.css', '--on-white-muted: #666666;', '--on-white-muted: #E6E6E6;'));

brokenFixture('severity conveyed without a text label', 'rule 19', (dir) =>
  patch(dir, 'index.html', (html) => html.replace(/<span>(High|Medium|Low) severity<\/span>/g, '')));

brokenFixture('a heatmap cell with no printed value', 'rule 19', (dir) =>
  patch(dir, 'index.html', (html) =>
    html.replace(/<span class="cell__value">[\s\S]*?<\/span><\/span>/g, '</span>')));

brokenFixture('an image with no alt attribute', 'rule 20', (dir) =>
  replace(dir, 'index.html', '<img src="assets/logo-slalom-white.svg" alt="Slalom">',
    '<img src="assets/logo-slalom-white.svg">'));

brokenFixture('a skipped heading level', 'rule 20', (dir) =>
  replace(dir, 'index.html', '<h2 class="headline" id="s1-purpose-scope-title">',
    '<h4 class="headline" id="s1-purpose-scope-title">'));

brokenFixture('a suppressed focus outline', 'rule 20', (dir) =>
  replace(dir, 'css/base.css', 'outline: 3px solid var(--focus-color);', 'outline: none;'));

brokenFixture('a missing reduced-motion block', 'rule 21', (dir) =>
  patch(dir, 'css/components.css', (css) =>
    css.replace('@media (prefers-reduced-motion: reduce) {', '@media (min-width: 1px) {')));

brokenFixture('reduced motion that skips instead of finalising', 'rule 21', (dir) =>
  replace(dir, 'css/components.css', 'opacity: 1 !important;', 'opacity: 0 !important;'));

brokenFixture('a data-motion value with no recipe', 'rule 21', (dir) =>
  replace(dir, 'index.html', 'data-motion="fade-up"', 'data-motion="zoom-blast"'));

// --- Delivery and confidentiality -------------------------------------------

brokenFixture('an external image', 'rule 22', (dir) =>
  replace(dir, 'index.html', '<main id="main">',
    '<main id="main"><img src="https://tracker.example.com/pixel.gif" alt="">'));

brokenFixture('a CDN stylesheet', 'rule 22', (dir) =>
  replace(dir, 'index.html', '<link rel="stylesheet" href="css/tokens.css">',
    '<link rel="stylesheet" href="//cdn.example.com/reset.css"><link rel="stylesheet" href="css/tokens.css">'));

brokenFixture('an external font import in CSS', 'rule 22', (dir) =>
  append(dir, 'css/base.css', '\n@font-face { font-family: X; src: url(https://fonts.example.com/x.woff2); }\n'));

brokenFixture('an absolute asset path', 'rule 23', (dir) =>
  replace(dir, 'index.html', 'src="assets/logo-slalom-white.svg"', 'src="/assets/logo-slalom-white.svg"'));

brokenFixture('a missing classification on the cover', 'rule 24', (dir) =>
  patch(dir, 'index.html', (html) =>
    html.replace('<p class="classification">Internal draft</p>', '')));

brokenFixture('an unlinked print stylesheet', 'rule 25', (dir) =>
  patch(dir, 'index.html', (html) =>
    html.replace('  <link rel="stylesheet" href="css/print.css">\n', '')));

brokenFixture('print styles that leave animation unresolved', 'rule 25', (dir) =>
  patch(dir, 'css/print.css', (css) => css.replace('opacity: 1 !important;', 'opacity: 0.5;')));

brokenFixture("a missing Anime.js licence", 'rule 26', (dir) =>
  rmSync(path.join(dir, 'js/LICENSE.md')));

brokenFixture('a shipped desktop font', 'rule 27', (dir) =>
  writeFileSync(path.join(dir, 'fonts/SlalomSans-Bold.otf'), 'not really a font'));

brokenFixture('an @font-face with no woff fallback', 'rule 27', (dir) =>
  patch(dir, 'css/base.css', (css) =>
    css.replace(/,\n\s*url\("\.\.\/fonts\/slalom-sans-light\.woff"\) format\("woff"\)/, '')));

/* ==========================================================================
   Run
   ========================================================================== */

registerDeliveryTests(test, TMP);

let passed = 0;
const failures = [];

console.log('');
for (const { name, fn } of tests) {
  if (only && !name.includes(only)) continue;
  try {
    await fn();
    passed++;
    console.log(`  ${style.green('ok')}   ${name}`);
  } catch (err) {
    failures.push({ name, err });
    console.log(`  ${style.red('FAIL')} ${name}`);
    console.log(`       ${String(err.message).split('\n').join('\n       ')}`);
  }
}

console.log('');
console.log(`  ${passed} passed · ${failures.length ? style.red(`${failures.length} failed`) : style.green('0 failed')} · ${tests.length} total`);
console.log('');
if (failures.length) process.exitCode = 1;
