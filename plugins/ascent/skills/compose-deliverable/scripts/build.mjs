#!/usr/bin/env node

import {
  copyFileSync, existsSync, mkdirSync, readFileSync, realpathSync, statSync, writeFileSync,
} from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import {
  parseContentFile, resolveSectionType, validateContent,
} from '../../create-deliverables/scripts/lib/content.mjs';

const SCRIPT_ROOT = path.dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = path.resolve(SCRIPT_ROOT, '..');
const CREATE_DELIVERABLES_ROOT = path.resolve(SKILL_ROOT, '../create-deliverables');
const BRAND_ROOT = path.resolve(SKILL_ROOT, '../utilities-ui-generation/branding/packs/slalom');
const TOKENS = JSON.parse(readFileSync(path.join(SKILL_ROOT, 'assets/powerpoint-tokens.json'), 'utf8'));
const COLLECTION_FIELDS = {
  'kpi-row': 'items', 'theme-group': 'findings', recommendations: 'items',
  roadmap: 'phases', heatmap: 'rows', 'next-steps': 'items',
};
const SECTION_LABELS = {
  'exec-summary': 'Summary', 'kpi-row': 'By the numbers', 'theme-group': 'Findings',
  recommendations: 'Recommendations', roadmap: 'Roadmap', quote: 'Perspective',
  heatmap: 'Assessment', 'next-steps': 'Next steps', methodology: 'Method',
};

function parseArgs(argv) {
  const options = { content: null, out: null, storyboard: null, htmlOnly: false };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === '--out') options.out = argv[++index];
    else if (argument === '--storyboard') options.storyboard = argv[++index];
    else if (argument === '--html-only') options.htmlOnly = true;
    else if (argument === '--help' || argument === '-h') options.help = true;
    else if (argument.startsWith('-')) throw new Error(`unknown option \`${argument}\``);
    else if (!options.content) options.content = argument;
    else throw new Error(`unexpected argument \`${argument}\``);
  }
  return options;
}

const USAGE = `
  node scripts/build.mjs <content.yaml|json> --out <deck.pptx> [--storyboard storyboard.json] [--html-only]
`;

function escapeHtml(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;');
}

function plainProse(value) {
  return String(value).replaceAll(/\*\*([^*]+)\*\*/g, '$1').replaceAll(/\*([^*]+)\*/g, '$1')
    .split(/\n\s*\n/).map((paragraph) => paragraph.trim()).filter(Boolean);
}

function notesTemplate(lines) {
  const unique = [...new Set(lines.filter(Boolean))];
  return `<template data-pptx-notes>${escapeHtml(`[Sources]\n${unique.map((line) => `- ${line}`).join('\n')}`)}</template>`;
}

function slideFrame(content, { sectionIndex = null, eyebrow = '', title = '', footer, notes }) {
  const sectionAttribute = sectionIndex === null ? '' : ` data-source-section="${sectionIndex}"`;
  return `
    <section class="slide"${sectionAttribute}>
      ${notesTemplate(notes)}
      <div class="top-rule"></div>
      ${eyebrow ? `<p class="eyebrow">${escapeHtml(eyebrow)}</p>` : ''}
      ${title ? `<h2>${escapeHtml(title)}</h2>` : ''}
      <div class="slide-content">${content}</div>
      <p class="footer">${escapeHtml(footer)}</p>
      <img class="content-logo" src="assets/slalom-logo-dark-blue-RGB.svg" alt="Slalom">
    </section>`;
}

function collectionField(section) {
  return COLLECTION_FIELDS[resolveSectionType(section.type)] ?? null;
}

function loadStoryboard(storyboardPath, document) {
  if (!storyboardPath) return document.sections.map((section, sectionIndex) => ({ section, sectionIndex }));
  let storyboard;
  try { storyboard = JSON.parse(readFileSync(storyboardPath, 'utf8')); }
  catch (error) { throw new Error(`cannot read storyboard \`${storyboardPath}\`: ${error.message}`); }
  if (!storyboard || typeof storyboard !== 'object' || Array.isArray(storyboard)) {
    throw new Error('storyboard must be a JSON object');
  }
  const unknownTopLevel = Object.keys(storyboard).filter((key) => !['version', 'slides'].includes(key));
  if (unknownTopLevel.length) throw new Error(`storyboard has unknown key \`${unknownTopLevel[0]}\``);
  if (storyboard.version !== 1) throw new Error('storyboard.version must be 1');
  if (!Array.isArray(storyboard.slides) || storyboard.slides.length === 0) {
    throw new Error('storyboard.slides must be a non-empty list');
  }

  const units = [];
  let previousSection = -1;
  const coverage = document.sections.map((section) => {
    const field = collectionField(section);
    return field ? Array(section[field].length).fill(0) : [0];
  });
  storyboard.slides.forEach((entry, storyboardIndex) => {
    const where = `storyboard.slides[${storyboardIndex}]`;
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) throw new Error(`${where} must be an object`);
    const unknown = Object.keys(entry).filter((key) => !['section', 'range', 'title', 'eyebrow'].includes(key));
    if (unknown.length) throw new Error(`${where} has unknown key \`${unknown[0]}\``);
    if (!Number.isInteger(entry.section) || entry.section < 0 || entry.section >= document.sections.length) {
      throw new Error(`${where}.section must identify an existing zero-based section`);
    }
    if (entry.section < previousSection) throw new Error(`${where} moves backward in source-section order`);
    previousSection = entry.section;
    const original = document.sections[entry.section];
    const field = collectionField(original);
    let section = { ...original };
    let range = null;
    if (entry.range !== undefined) {
      if (!field) throw new Error(`${where}.range is not valid for section type \`${original.type}\``);
      if (!Array.isArray(entry.range) || entry.range.length !== 2 || !entry.range.every(Number.isInteger)) {
        throw new Error(`${where}.range must be [start, end] using zero-based, end-exclusive integers`);
      }
      const [start, end] = entry.range;
      if (start < 0 || start >= end || end > original[field].length) {
        throw new Error(`${where}.range [${start}, ${end}] is outside ${field}[0:${original[field].length}]`);
      }
      range = [start, end];
      section = { ...section, [field]: original[field].slice(start, end) };
      for (let item = start; item < end; item += 1) coverage[entry.section][item] += 1;
    } else coverage[entry.section] = coverage[entry.section].map((count) => count + 1);
    if (entry.title !== undefined && typeof entry.title !== 'string') throw new Error(`${where}.title must be text`);
    if (entry.eyebrow !== undefined && typeof entry.eyebrow !== 'string') throw new Error(`${where}.eyebrow must be text`);
    units.push({ section, sectionIndex: entry.section, range, title: entry.title, eyebrow: entry.eyebrow });
  });
  coverage.forEach((counts, sectionIndex) => {
    const missing = counts.map((count, index) => (count === 0 ? index : null)).filter((index) => index !== null);
    const repeated = counts.map((count, index) => (count > 1 ? index : null)).filter((index) => index !== null);
    if (missing.length) throw new Error(`storyboard does not cover section ${sectionIndex} item(s): ${missing.join(', ')}`);
    if (repeated.length) throw new Error(`storyboard repeats section ${sectionIndex} item(s): ${repeated.join(', ')}`);
  });
  return units;
}

function sectionTitle(section) {
  const type = resolveSectionType(section.type);
  return section.title || {
    'exec-summary': 'In brief', recommendations: 'Recommendations', roadmap: 'Roadmap',
    'next-steps': 'Next steps', methodology: 'Methodology',
  }[type] || section.type;
}

function collectSourceLabels(section) {
  return resolveSectionType(section.type) === 'kpi-row'
    ? section.items.map((item) => `Source: ${item.source}`) : [];
}

function renderSection(unit, slideIndex, meta, fixtureName) {
  const { section, sectionIndex } = unit;
  const type = resolveSectionType(section.type);
  const title = unit.title || sectionTitle(section);
  let content;
  if (type === 'exec-summary' || type === 'methodology') {
    content = `<div class="prose">${plainProse(section.body).map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join('')}</div>`;
  } else if (type === 'kpi-row') {
    content = `<div class="kpi-grid">${section.items.map((item) => `
      <article class="kpi"><p class="kpi-value">${escapeHtml(item.value)}${item.unit ? ` ${escapeHtml(item.unit)}` : ''}</p>
      <p class="kpi-label">${escapeHtml(item.label)}</p><p class="source">Source: ${escapeHtml(item.source)}</p></article>`).join('')}</div>`;
  } else if (type === 'theme-group') {
    const showIntro = section.body && (!unit.range || unit.range[0] === 0);
    content = `${showIntro ? `<p class="intro">${escapeHtml(section.body)}</p>` : ''}
      <div class="finding-grid finding-grid--${section.findings.length}">${section.findings.map((finding) => `
        <article class="finding"><p class="severity">${escapeHtml(finding.severity || 'Not rated')} severity</p>
        ${title === finding.theme ? '' : `<h3>${escapeHtml(finding.theme)}</h3>`}<p><strong>Evidence</strong> ${escapeHtml(finding.evidence)}</p>
        <p><strong>Implication</strong> ${escapeHtml(finding.implication)}</p></article>`).join('')}</div>`;
  } else if (type === 'recommendations') {
    content = `<div class="stack">${section.items.map((item) => `
      <article class="row recommendation"><div class="number">${escapeHtml(item.horizon || 'Action')}</div>
      <div><h3>${escapeHtml(item.action)}</h3><p>${escapeHtml(item.rationale)}</p>${item.owner ? `<p class="source">Owner: ${escapeHtml(item.owner)}</p>` : ''}</div></article>`).join('')}</div>`;
  } else if (type === 'roadmap') {
    content = `<div class="roadmap">${section.phases.map((phase) => `
      <article class="phase"><p class="severity">${escapeHtml(phase.window)}</p><h3>${escapeHtml(phase.name)}</h3>
      <ul>${phase.outcomes.map((outcome) => `<li>${escapeHtml(outcome)}</li>`).join('')}</ul></article>`).join('')}</div>`;
  } else if (type === 'quote') {
    content = `<blockquote>“${escapeHtml(section.quote)}”</blockquote><p class="attribution">${escapeHtml(section.name)}${section.attribution_title ? ` · ${escapeHtml(section.attribution_title)}` : ''}</p>`;
  } else if (type === 'heatmap') {
    content = `<div class="heatmap">${section.rows.map((row) => `<article class="row"><div><h3>${escapeHtml(row.capability)}</h3>${row.note ? `<p>${escapeHtml(row.note)}</p>` : ''}</div><p class="score">${row.values.map((value, valueIndex) => `${escapeHtml(section.columns[valueIndex])}: ${value} of 5`).join(' · ')}</p></article>`).join('')}</div>`;
  } else if (type === 'next-steps') {
    content = `<ol class="next-steps">${section.items.map((item, itemIndex) => `<li><span class="step-index">${itemIndex + 1}</span><span>${escapeHtml(item)}</span></li>`).join('')}</ol>`;
  } else throw new Error(`renderer does not support section type \`${section.type}\``);

  const sourceLabels = collectSourceLabels(section);
  return {
    html: slideFrame(content, {
      sectionIndex,
      eyebrow: unit.eyebrow || `${String(slideIndex + 1).padStart(2, '0')} · ${SECTION_LABELS[type] || type}`,
      title, footer: `${meta.classification} · ${meta.date}`,
      notes: [`Approved content fixture: ${fixtureName}`, ...sourceLabels],
    }),
    manifest: {
      kind: 'content', sourceSection: sectionIndex, sourceType: section.type, sourceRange: unit.range,
      title, expectedText: [title, meta.classification], expectedSourceLabels: sourceLabels,
      requiresNativeText: true, requiresNativeShapes: true, requiresLogo: true, requiresSourcesNotes: true,
    },
  };
}

function prepareAssets(document, contentPath, outputDirectory) {
  const assetDirectory = path.join(outputDirectory, 'assets');
  mkdirSync(assetDirectory, { recursive: true });
  for (const logo of ['slalom-logo-white-RGB.svg', 'slalom-logo-dark-blue-RGB.svg']) {
    copyFileSync(path.join(BRAND_ROOT, 'assets/logos', logo), path.join(assetDirectory, logo));
  }
  let clientLogoFile = null;
  if (document.meta.client_logo) {
    const contentDirectory = realpathSync(path.dirname(contentPath));
    const requested = path.resolve(contentDirectory, document.meta.client_logo);
    if (!existsSync(requested)) throw new Error(`client_logo does not exist: ${document.meta.client_logo}`);
    const resolved = realpathSync(requested);
    const relative = path.relative(contentDirectory, resolved);
    if (relative.startsWith('..') || path.isAbsolute(relative)) {
      throw new Error('client_logo must stay inside the approved content directory');
    }
    const extension = path.extname(resolved).toLowerCase();
    if (!['.svg', '.png'].includes(extension)) throw new Error('client_logo must be a trusted local .svg or .png file');
    if (!statSync(resolved).isFile()) throw new Error('client_logo must resolve to a regular file');
    if (statSync(resolved).size > 5 * 1024 * 1024) throw new Error('client_logo exceeds the 5 MB trusted-file limit');
    clientLogoFile = `client-logo${extension}`;
    copyFileSync(resolved, path.join(assetDirectory, clientLogoFile));
  }
  return { clientLogoFile };
}

function renderHtml(document, units, assets, fixtureName) {
  const { meta } = document;
  const accent = TOKENS.secondary[meta.accent];
  const { stage, primary: colors, neutral, font } = TOKENS;
  const coverLockup = assets.clientLogoFile
    ? `<div class="partner-lockup"><img class="logo" src="assets/slalom-logo-white-RGB.svg" alt="Slalom"><span class="partner-divider"></span><img class="client-logo" src="assets/${escapeHtml(assets.clientLogoFile)}" alt="${escapeHtml(meta.client)}"></div>`
    : '<img class="logo" src="assets/slalom-logo-white-RGB.svg" alt="Slalom">';
  const cover = `
    <section class="slide cover" data-slide-kind="cover">${notesTemplate([`Approved content fixture: ${fixtureName}`])}
      ${coverLockup}<p class="cover-client">${escapeHtml(meta.client)}</p><h1>${escapeHtml(meta.title)}</h1>
      ${meta.subtitle ? `<p class="subtitle">${escapeHtml(meta.subtitle)}</p>` : ''}<div class="accent-bar"></div>
      <p class="cover-meta">${escapeHtml(meta.classification)} · ${escapeHtml(meta.date)}</p></section>`;
  const rendered = units.map((unit, index) => renderSection(unit, index, meta, fixtureName));
  const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=${stage.widthPixels}, initial-scale=1">
<title>${escapeHtml(meta.title)}</title><style>
:root { --blue: ${colors.slalomBlue}; --dark-blue: ${colors.slalomDarkBlue}; --accent: ${accent}; --white: ${neutral.white}; --light-gray: ${neutral.lightGray}; --dark-gray: ${neutral.darkGray}; --black: ${neutral.black}; }
* { box-sizing: border-box; } html, body { margin: 0; padding: 0; background: var(--light-gray); }
body { font-family: "${font.powerPoint}", "${font.fallback}", sans-serif; }
.slide { position: relative; width: ${stage.widthPixels}px; height: ${stage.heightPixels}px; overflow: hidden; margin: 0 0 32px; padding: 104px 120px 92px; background: var(--white); color: var(--black); }
.cover { padding: 102px 132px; background: var(--blue); color: var(--white); }
.logo { position: absolute; top: 78px; right: 104px; width: 190px; height: 70px; object-fit: contain; }
.partner-lockup { position: absolute; top: 70px; right: 104px; display: flex; align-items: center; gap: 24px; height: 86px; }
.partner-lockup .logo { position: static; width: 190px; height: 70px; } .partner-divider { width: 3px; height: 78px; background: var(--white); }
.client-logo { width: 190px; height: 76px; object-fit: contain; } .cover-client { margin: 160px 0 20px; font-size: 32px; font-weight: 700; }
h1 { width: 1510px; margin: 0; font-size: 104px; line-height: .98; font-weight: 700; }
.subtitle { width: 1340px; margin: 32px 0 0; font-size: 48px; line-height: 1.15; }
.accent-bar { position: absolute; left: 132px; bottom: 118px; width: 420px; height: 18px; background: var(--accent); }
.cover-meta { position: absolute; left: 132px; bottom: 62px; width: 900px; margin: 0; font-size: 22px; white-space: nowrap; }
.top-rule { position: absolute; top: 0; left: 0; width: 100%; height: 18px; background: var(--blue); }
.eyebrow { margin: 0 0 16px; color: var(--dark-blue); font-size: 24px; font-weight: 700; }
h2 { width: 1680px; margin: 0; color: var(--black); font-size: 70px; line-height: 1.02; white-space: nowrap; }
.slide-content { margin-top: 42px; } .footer { position: absolute; left: 120px; right: 310px; bottom: 34px; margin: 0; color: var(--dark-gray); font-size: 20px; }
.content-logo { position: absolute; right: 120px; bottom: 25px; width: 150px; height: 42px; object-fit: contain; }
.prose { width: 1500px; border-left: 14px solid var(--accent); padding-left: 42px; } .prose p, .intro { margin: 0 0 24px; font-size: 36px; line-height: 1.28; }
.finding-grid, .kpi-grid, .roadmap { display: flex; gap: 30px; align-items: stretch; } .finding, .kpi, .phase { flex: 1; min-width: 0; padding: 28px 32px; border: 2px solid var(--light-gray); border-top: 12px solid var(--accent); }
.finding-grid--1 .finding { max-width: 1510px; border-left-color: var(--accent); } h3 { margin: 0 0 14px; font-size: 48px; line-height: 1.05; }
.finding p, .phase li, .row p { margin: 8px 0; font-size: 32px; line-height: 1.22; } .finding strong { color: var(--dark-blue); }
.severity, .source { color: var(--dark-gray); font-size: 24px !important; font-weight: 700; } .kpi-value { margin: 0; color: var(--blue); font-size: 76px; line-height: 1; font-weight: 700; white-space: nowrap; }
.kpi-label { font-size: 34px; line-height: 1.15; } .stack, .heatmap { display: flex; flex-direction: column; gap: 14px; }
.row { display: flex; gap: 32px; align-items: flex-start; padding: 22px 20px; border-bottom: 2px solid var(--light-gray); } .row > div:last-child { flex: 1; }
.number { min-width: 220px; color: var(--dark-blue); font-size: 26px; font-weight: 700; } .recommendation h3 { font-size: 38px; } .recommendation p { font-size: 29px; }
.score { margin-left: auto !important; color: var(--dark-blue); font-weight: 700; white-space: nowrap; } blockquote { width: 1500px; margin: 72px 0 32px; color: var(--dark-blue); font-size: 64px; line-height: 1.12; font-weight: 700; }
.attribution { font-size: 30px; } .next-steps { width: 1510px; margin: 0; padding: 0; list-style: none; }
.next-steps li { display: grid; grid-template-columns: 52px 1fr; gap: 24px; margin: 0; padding: 22px 0; border-bottom: 2px solid var(--light-gray); font-size: 34px; line-height: 1.18; }
.step-index { color: var(--blue); font-weight: 700; } .phase h3 { font-size: 40px; } .phase li { font-size: 32px; margin-bottom: 10px; }
</style></head><body>${cover}${rendered.map((item) => item.html).join('')}</body></html>`;
  return { html, slideManifests: rendered.map((item) => item.manifest) };
}

function writeManifest(document, slideManifests, outputPath, contentPath, storyboardPath, assets) {
  const sectionSlides = document.sections.map(() => []);
  slideManifests.forEach((slide, index) => sectionSlides[slide.sourceSection].push(index + 2));
  const manifest = {
    schemaVersion: 1, input: path.basename(contentPath), storyboard: storyboardPath ? path.basename(storyboardPath) : null,
    title: document.meta.title, classification: document.meta.classification, font: TOKENS.font.powerPoint,
    allowedColors: [...Object.values(TOKENS.primary), ...Object.values(TOKENS.secondary), ...Object.values(TOKENS.neutral)]
      .map((value) => value.replace('#', '').toUpperCase()),
    slideSize: { widthInches: TOKENS.stage.widthInches, heightInches: TOKENS.stage.heightInches, orientation: 'landscape' },
    assets: { slalomLogos: ['slalom-logo-white-RGB.svg', 'slalom-logo-dark-blue-RGB.svg'], clientLogo: assets.clientLogoFile },
    sections: document.sections.map((section, index) => ({ index, type: section.type, title: sectionTitle(section), slideNumbers: sectionSlides[index] })),
    slides: [{
      number: 1, kind: 'cover', expectedText: [document.meta.title, document.meta.classification], expectedSourceLabels: [],
      requiresNativeText: true, requiresNativeShapes: true, requiresLogo: true, requiresSourcesNotes: true,
    }, ...slideManifests.map((slide, index) => ({ number: index + 2, ...slide }))],
  };
  const manifestPath = outputPath.replace(/\.pptx$/i, '.manifest.json');
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  return manifestPath;
}

function runPreviewValidation(previewPath, manifestPath) {
  const result = spawnSync(process.execPath, [path.join(SKILL_ROOT, 'scripts/validate_preview.mjs'), previewPath, '--manifest', manifestPath], {
    cwd: SKILL_ROOT, encoding: 'utf8',
  });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`HTML preview validation failed with status ${result.status}`);
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) { process.stdout.write(USAGE); return; }
  if (!options.content || !options.out) throw new Error(`content and --out are required\n${USAGE}`);
  const contentPath = path.resolve(options.content);
  const outputPath = path.resolve(options.out);
  const storyboardPath = options.storyboard ? path.resolve(options.storyboard) : null;
  if (path.extname(outputPath).toLowerCase() !== '.pptx') throw new Error('--out must end in .pptx');
  const document = parseContentFile(contentPath);
  const archetypePath = path.join(CREATE_DELIVERABLES_ROOT, 'templates', document.meta?.archetype || '', 'archetype.json');
  const archetype = JSON.parse(readFileSync(archetypePath, 'utf8'));
  archetype.name ||= document.meta.archetype;
  validateContent(document, { archetype });
  const units = loadStoryboard(storyboardPath, document);
  const outputDirectory = path.dirname(outputPath);
  const previewPath = outputPath.replace(/\.pptx$/i, '.html');
  mkdirSync(outputDirectory, { recursive: true });
  const assets = prepareAssets(document, contentPath, outputDirectory);
  const { html, slideManifests } = renderHtml(document, units, assets, path.basename(contentPath));
  writeFileSync(previewPath, html, 'utf8');
  const manifestPath = writeManifest(document, slideManifests, outputPath, contentPath, storyboardPath, assets);
  process.stdout.write(`Preview: ${previewPath}\nManifest: ${manifestPath}\n`);
  runPreviewValidation(previewPath, manifestPath);
  if (options.htmlOnly) return;
  const cli = path.join(SKILL_ROOT, 'node_modules/dom-to-pptx/bin/cli-main.js');
  const stage = TOKENS.stage;
  const result = spawnSync(process.execPath, [cli, 'export', previewPath, '--output', outputPath, '--selector', '.slide',
    '--inject', '--title', document.meta.title, '--author', 'Slalom', '--width', String(stage.widthInches),
    '--height', String(stage.heightInches), '--browser-width', String(stage.widthPixels), '--browser-height', String(stage.heightPixels), '--no-pseudo'],
  { cwd: SKILL_ROOT, encoding: 'utf8', stdio: 'inherit' });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`dom-to-pptx export failed with status ${result.status}`);
  process.stdout.write(`Deck: ${outputPath}\n`);
}

try { main(); }
catch (error) { process.stderr.write(`${error.name || 'Error'}: ${error.message}\n`); process.exitCode = 1; }
