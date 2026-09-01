#!/usr/bin/env node

import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const TEST_ROOT = path.dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = path.resolve(TEST_ROOT, '../..');
const BUILD_SCRIPT = path.join(SKILL_ROOT, 'scripts/build.mjs');
const FIXTURE = path.join(SKILL_ROOT, 'examples/reference-informed-content.yaml');
const STORYBOARD = path.join(SKILL_ROOT, 'examples/reference-informed-storyboard.json');
const VALIDATOR = path.join(SKILL_ROOT, 'scripts/validate_pptx.py');
const VALIDATOR_CASES = path.join(SKILL_ROOT, 'scripts/test/validator_cases.py');

function run(args) {
  return spawnSync(process.execPath, [BUILD_SCRIPT, ...args], {
    cwd: SKILL_ROOT,
    encoding: 'utf8',
  });
}

function runPython(script, args) {
  return spawnSync('python3', [script, ...args], { cwd: SKILL_ROOT, encoding: 'utf8' });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const temporary = mkdtempSync(path.join(os.tmpdir(), 'compose-deliverable-test-'));
try {
  const output = path.join(temporary, 'demo.pptx');
  const valid = run([FIXTURE, '--storyboard', STORYBOARD, '--out', output, '--html-only']);
  assert(valid.status === 0, `valid fixture failed:\n${valid.stderr}`);

  const html = readFileSync(output.replace(/\.pptx$/, '.html'), 'utf8');
  assert(html.includes('class="slide cover"'), 'cover slide was not rendered');
  assert(html.includes('class="slide"'), 'content slides were not rendered');
  assert(html.includes('Avenir Next LT Pro'), 'PowerPoint typeface is absent');
  assert(html.includes('--blue: #0C62FB'), 'Slalom Blue token is absent');
  assert(!html.includes('https://'), 'conversion preview must not make external requests');
  assert(!html.includes('counter(steps)'), 'next-step numbers must be native text, not pseudo-elements');
  assert(html.includes('class="step-index">1</span>'), 'native next-step numbering is absent');

  const manifest = JSON.parse(readFileSync(output.replace(/\.pptx$/, '.manifest.json'), 'utf8'));
  assert(manifest.slides.length === 11, `expected 11 storyboard slides, found ${manifest.slides.length}`);
  assert(manifest.sections.every((section) => section.slideNumbers.length > 0), 'every source section must map to at least one slide');

  const invalidFixture = path.join(temporary, 'invalid.yaml');
  writeFileSync(invalidFixture, readFileSync(FIXTURE, 'utf8').replace(
    '  accent: cyan',
    '  accent: cyan\n  invented_metric: 7000x',
  ));
  const invalid = run([invalidFixture, '--storyboard', STORYBOARD, '--out', path.join(temporary, 'invalid.pptx'), '--html-only']);
  assert(invalid.status !== 0, 'unknown content fields must fail validation');
  assert(invalid.stderr.includes('unknown key `invented_metric`'), 'validation failure did not name the unknown field');

  const incompleteStoryboard = path.join(temporary, 'incomplete-storyboard.json');
  writeFileSync(incompleteStoryboard, JSON.stringify({ version: 1, slides: [{ section: 0 }] }));
  const incomplete = run([FIXTURE, '--storyboard', incompleteStoryboard, '--out', path.join(temporary, 'incomplete.pptx'), '--html-only']);
  assert(incomplete.status !== 0, 'an incomplete storyboard must fail');
  assert(incomplete.stderr.includes('storyboard does not cover section'), 'storyboard coverage failure was not business-readable');

  const overflowFixture = path.join(temporary, 'overflow.yaml');
  const overflowItems = Array.from({ length: 18 }, (_, index) => `      - Deliberately oversized preview item ${index + 1} proves overflow fails clearly.`).join('\n');
  writeFileSync(overflowFixture, readFileSync(FIXTURE, 'utf8').replace(
    '      - Establish a governance cadence that keeps adoption visible.',
    overflowItems,
  ));
  const overflow = run([overflowFixture, '--storyboard', STORYBOARD, '--out', path.join(temporary, 'overflow.pptx'), '--html-only']);
  assert(overflow.status !== 0, 'obvious HTML-stage overflow must fail');
  assert(overflow.stderr.includes('content exceeds the fixed stage'), 'overflow failure did not identify the fixed stage');

  const deck = path.join(temporary, 'reference-informed.pptx');
  const fullBuild = run([FIXTURE, '--storyboard', STORYBOARD, '--out', deck]);
  assert(fullBuild.status === 0, `full PPTX build failed:\n${fullBuild.stderr}`);
  const deckManifest = deck.replace(/\.pptx$/, '.manifest.json');
  const structural = runPython(VALIDATOR, [deck, '--manifest', deckManifest]);
  assert(structural.status === 0, `structural validation failed:\n${structural.stderr}`);
  const brokenCases = runPython(VALIDATOR_CASES, [deck, deckManifest]);
  assert(brokenCases.status === 0, `negative validator cases failed:\n${brokenCases.stderr}`);

  process.stdout.write('PASS: compose-deliverable renderer and validator tests\n');
} finally {
  rmSync(temporary, { recursive: true, force: true });
}
