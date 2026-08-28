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
import { build, loadArchetype } from '../build.mjs';
import { validateBuild } from '../validate-brand.mjs';
import { writeBundle } from '../lib/bundle.mjs';
import { style } from '../lib/report.mjs';

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

const ARCHETYPE = loadArchetype('executive-readout');
const ICONS = listIconNames();

function content(overrides = {}) {
  const base = {
    meta: {
      archetype: 'executive-readout',
      client: 'Test Client',
      title: 'A minimal readout',
      date: '2026-01-15',
      classification: 'Confidential — prepared for Test Client',
      accent: 'cyan',
    },
    sections: [
      { type: 'exec-summary', body: 'One paragraph.' },
      {
        type: 'theme-group',
        title: 'What we heard',
        findings: [{ theme: 'T', evidence: 'E', implication: 'I' }],
      },
      { type: 'recommendations', items: [{ action: 'A', rationale: 'R' }] },
      { type: 'next-steps', items: ['One'] },
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
  const narrow = { ...ARCHETYPE, allowed_sections: ['exec-summary'] };
  const err = throws(() => validateContent(content(), { archetype: narrow, iconNames: ICONS }));
  includes(err.message, 'does not permit a `theme-group` section');
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
  delete doc.sections[1].findings[0].implication;
  contentError(doc, 'missing required field `implication`');
});

test('content: an unapproved icon is an error', () => {
  const doc = content();
  doc.sections[1].findings[0].icon = 'sparkle-magic';
  contentError(doc, 'is not an approved icon');
});

test('content: a severity outside high/medium/low is an error', () => {
  const doc = content();
  doc.sections[1].findings[0].severity = 'critical';
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

const EXAMPLE = path.join(SKILL_ROOT, 'templates', 'executive-readout', 'content.example.yaml');
const FIXTURES = path.join(SKILL_ROOT, 'scripts', 'test', 'fixtures');

let example = null;   // the reference build, shared by the validator tests

test('build: the worked example builds end to end', () => {
  example = build(EXAMPLE, { out: path.join(TMP, 'example'), bundle: true });
  ok(existsSync(path.join(example.outDir, 'index.html')));
  eq(example.manifest.archetype, 'executive-readout');
  eq(example.manifest.accent, 'cyan');
});

test('build: the output folder has the expected structure', () => {
  for (const rel of [
    'index.html', 'bundle.html', 'brand-manifest.json',
    'css/tokens.css', 'css/base.css', 'css/components.css', 'css/print.css',
    'js/motion.js', 'js/anime.esm.min.js', 'js/LICENSE.md',
    'assets/logo-slalom-white.svg',
  ]) {
    ok(existsSync(path.join(example.outDir, rel)), `missing ${rel}`);
  }
});

test('build: data-accent is set on <html> from meta.accent', () => {
  includes(example.html, '<html lang="en" data-accent="cyan">');
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
  eq(example.manifest.icons.sort(), ['line-graph', 'network', 'people', 'search']);
  ok(!existsSync(path.join(example.outDir, 'assets/icon-coffee.svg')));
});

test('build: a JSON content file is a first-class input', () => {
  const result = build(path.join(FIXTURES, 'valid-minimal.json'), { out: path.join(TMP, 'json') });
  includes(result.html, 'A minimal readout');
  eq(result.manifest.accent, 'chartreuse');
});

test('build: the long-content layout stress fixture builds', () => {
  const result = build(path.join(FIXTURES, 'layout-stress.json'), { out: path.join(TMP, 'layout-stress') });
  includes(result.html, 'A deliberately long KPI value');
  includes(result.html, 'A recommendation title designed to exercise wrapping');
});

test('layout: components keep content visible and constrain data-driven columns', () => {
  const baseCss = readFileSync(path.join(SKILL_ROOT, 'assets', 'css', 'base.css'), 'utf8');
  const componentsCss = readFileSync(path.join(SKILL_ROOT, 'assets', 'css', 'components.css'), 'utf8');
  ok(!/overflow-x:\s*hidden/.test(baseCss), 'page-level horizontal overflow must not hide layout failures');
  includes(componentsCss, 'container-type: inline-size;', 'KPI tiles need container-aware typography');
  includes(componentsCss, 'minmax(10rem, 18rem)', 'recommendation metadata needs a bounded column');
  includes(componentsCss, 'overflow-wrap: anywhere;', 'long client-provided content must be able to wrap');
});

test('build: the minimal YAML fixture and its JSON twin render identically', () => {
  const y = build(path.join(FIXTURES, 'valid-minimal.yaml'), { out: path.join(TMP, 'yaml') });
  const j = build(path.join(FIXTURES, 'valid-minimal.json'), { out: path.join(TMP, 'json2') });
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
  includes(example.html, 'data-count-to="34"');
});

test('build: content is escaped, not injected', () => {
  const doc = content();
  doc.meta.client = '<script>alert(1)</script>';
  writeFileSync(path.join(TMP, 'xss.json'), JSON.stringify(doc));
  const result = build(path.join(TMP, 'xss.json'), { out: path.join(TMP, 'xss') });
  ok(!result.html.includes('<script>alert(1)</script>'), 'unescaped content reached the output');
  includes(result.html, '&lt;script&gt;');
});

/* ==========================================================================
   4. --bundle
   ========================================================================== */

test('bundle: the single file has no external reference and stands alone', () => {
  const bundle = readFileSync(path.join(example.outDir, 'bundle.html'), 'utf8');
  ok(!/<link\b[^>]*stylesheet/i.test(bundle), 'bundle.html still links a stylesheet');
  ok(!/<script\b[^>]*\ssrc=/i.test(bundle), 'bundle.html still loads a script by src');
  ok(!/\ssrc="assets\//.test(bundle), 'bundle.html still references an image file');
  ok(!/(?:src|href)="\s*(?:https?:)?\/\//i.test(bundle), 'bundle.html makes an external reference');
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
  replace(dir, 'index.html', '>What we heard</h2>', '>WHAT WE HEARD</h2>'));

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
  writeFileSync(path.join(dir, 'assets/icon-network.svg'),
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'));

brokenFixture('an icon reversed onto a dark surface', 'rule 16', (dir) =>
  replace(dir, 'index.html',
    '<section class="section surface-white" id="s3-what-we-heard"',
    '<section class="section surface-black" id="s3-what-we-heard"'));

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
  replace(dir, 'index.html', '<h2 class="headline" id="s1-in-brief-title">',
    '<h4 class="headline" id="s1-in-brief-title">'));

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
    html.replace('<p class="classification">Confidential — prepared for Northwind Health</p>', '')));

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

let passed = 0;
const failures = [];

console.log('');
for (const { name, fn } of tests) {
  if (only && !name.includes(only)) continue;
  try {
    fn();
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
