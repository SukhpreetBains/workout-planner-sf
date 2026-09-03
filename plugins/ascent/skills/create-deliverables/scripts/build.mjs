#!/usr/bin/env node
/**
 * build.mjs — content in, static microsite out.
 *
 *   node scripts/build.mjs <content.yaml|.json> [options]
 *
 *   --out <dir>       output directory (default ./build/<client>-<archetype>)
 *   --intake <file>   question coverage and evidence record for modular templates
 *   --preview-module  render only one module for isolated visual review
 *   --bundle          also emit bundle.html, everything inlined into one file
 *   --no-validate     skip the brand gate for iteration only
 *
 * The microsite is a pure function of the content file. Nobody hand-edits the
 * output: change the content and rebuild.
 */

import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';

import { ContentError, parseContentFile, resolveSectionType, validateContent } from './lib/content.mjs';
import {
  INCOMPLETE_CONSEQUENCES, decorateContentWithGaps, loadAndEvaluateIntake, loadModuleRenderers,
  loadTemplateModules, resolveGuidedContent,
} from './lib/intake.mjs';
import {
  AssetError, SKILL_ROOT, copyAssets, copyOwnAssets, listIconNames, logoVariantFor,
} from './lib/assets.mjs';
import {
  esc, railLabel, renderCover, renderFooter, renderRail, renderSection, sectionId,
} from '../templates/modules/shared/html.mjs';
import { Report, fatal, style } from './lib/report.mjs';
import { writeBundle } from './lib/bundle.mjs';
import { validateBuild } from './validate-brand.mjs';

/* ==========================================================================
   Arguments
   ========================================================================== */

function parseArgs(argv) {
  const opts = { content: null, out: null, intake: null, previewModule: null, bundle: false, validate: true };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--out') opts.out = argv[++i];
    else if (arg === '--intake') opts.intake = argv[++i];
    else if (arg === '--preview-module') opts.previewModule = argv[++i];
    else if (arg === '--bundle') opts.bundle = true;
    else if (arg === '--no-validate') opts.validate = false;
    else if (arg === '-h' || arg === '--help') opts.help = true;
    else if (arg.startsWith('-')) throw new Error(`unknown option \`${arg}\``);
    else if (!opts.content) opts.content = arg;
    else throw new Error(`unexpected argument \`${arg}\``);
  }
  if (!opts.out && opts.content === null && !opts.help) throw new Error('no content file given');
  return opts;
}

const USAGE = `
  node scripts/build.mjs <content.yaml|.json> [--intake <file>] [--preview-module <id>] [--out <dir>] [--bundle] [--no-validate]
`;

/* ==========================================================================
   Archetype
   ========================================================================== */

export function loadArchetype(name) {
  if (typeof name !== 'string' || !/^[a-z0-9-]+$/.test(name)) {
    throw new ContentError(`meta.archetype must name a template directory, found \`${name}\``);
  }
  const file = path.join(SKILL_ROOT, 'templates', name, 'archetype.json');
  if (!existsSync(file)) {
    throw new ContentError(
      `no archetype named \`${name}\`.\n  expected: ${file}\n  ` +
      'See references/archetypes.md for the archetypes that exist and how to add one.');
  }
  const manifest = JSON.parse(readFileSync(file, 'utf8'));
  manifest.name ??= name;
  return manifest;
}

/* ==========================================================================
   Render
   ========================================================================== */

function longDate(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
    .format(new Date(y, m - 1, d));
}

export function renderDocument(doc, ctx, moduleRenderers = new Map(), coverRenderer = null) {
  const { meta, sections } = doc;
  const railEntries = sections.map((section, i) => ({
    id: sectionId(section, i),
    label: railLabel(section),
  }));

  const body = sections.map((section, i) => {
    const renderer = section.module && section.view
      ? moduleRenderers.get(`${section.module}:${section.view}`)
      : null;
    return renderSection(section, i, ctx, renderer);
  }).join('\n');
  const description = meta.subtitle
    ? `${meta.title} — ${meta.subtitle}`
    : meta.title;

  return `<!doctype html>
<html lang="en" data-accent="${esc(meta.accent)}" data-deliverable-status="${esc(ctx.buildStatus ?? 'final')}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${esc(meta.title)} · ${esc(meta.client)}</title>
  <meta name="description" content="${esc(description)}">
  <meta name="author" content="Slalom">
  <!-- A client deliverable is not published content. -->
  <meta name="robots" content="noindex, nofollow, noarchive">
  <meta name="classification" content="${esc(meta.classification)}">
  <link rel="stylesheet" href="css/tokens.css">
  <link rel="stylesheet" href="css/base.css">
  <link rel="stylesheet" href="css/components.css">
  <link rel="stylesheet" href="css/print.css">
  <script type="importmap">{"imports":{"animejs":"./js/anime.esm.min.js"}}</script>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <div class="page">
${(coverRenderer ?? renderCover)(meta, ctx)}
${renderRail(railEntries)}
    <main id="main">
${body}
    </main>
${renderFooter(meta, ctx)}
  </div>
  <script type="module" src="js/motion.js"></script>
</body>
</html>
`;
}

/* ==========================================================================
   Build
   ========================================================================== */

export async function build(contentPath, {
  out = null, intake: intakePath = null, previewModule = null, bundle = false,
} = {}) {
  const absContent = path.resolve(contentPath);
  const contentDir = path.dirname(absContent);

  // 1. Parse, then resolve the archetype the content asks for, then validate
  //    against both the schema and that archetype's manifest.
  const raw = parseContentFile(absContent);
  const archetypeName = raw?.meta?.archetype;
  const archetype = loadArchetype(archetypeName);
  const modules = loadTemplateModules(archetype, SKILL_ROOT);
  const guidedRaw = resolveGuidedContent(raw, modules);
  const doc = validateContent(guidedRaw, { archetype, iconNames: listIconNames() });
  const { meta, sections } = doc;
  const moduleRenderers = await loadModuleRenderers(modules);
  const intake = modules.length
    ? loadAndEvaluateIntake(intakePath, archetype, modules)
    : null;
  let renderedDoc = decorateContentWithGaps(doc, intake, modules);
  if (previewModule) {
    if (!modules.some((module) => module.id === previewModule)) {
      throw new ContentError(`preview module \`${previewModule}\` is not selected by this template`);
    }
    const previewSections = renderedDoc.sections.filter((section) => section.module === previewModule);
    if (previewSections.length === 0) {
      throw new ContentError(`content has no authored sections for preview module \`${previewModule}\``);
    }
    renderedDoc = { ...renderedDoc, sections: previewSections };
  }

  // 2. Work out which brand assets this particular deliverable needs.
  const coverSurface = archetype.cover_surface ?? 'blue';
  const coverLogo = logoVariantFor(coverSurface);
  const footerLogo = logoVariantFor(archetype.footer_surface ?? 'black');
  const icons = sections.flatMap((s) =>
    resolveSectionType(s.type) === 'theme-group'
      ? s.findings.map((f) => f.icon).filter(Boolean)
      : []);
  const clientLogo = meta.client_logo ? path.resolve(contentDir, meta.client_logo) : null;

  const outDir = path.resolve(out ?? path.join(
    process.cwd(), 'build',
    `${slugify(meta.client)}-${archetype.name}`));

  if (existsSync(outDir)) rmSync(outDir, { recursive: true, force: true });
  mkdirSync(outDir, { recursive: true });

  const assets = copyAssets(outDir, {
    logoVariants: [coverLogo, footerLogo],
    icons,
    clientLogo,
  });
  copyOwnAssets(outDir);

  // 3. Render.
  const ctx = {
    meta,
    coverSurface,
    logoPath: assets.logos[coverLogo],
    footerLogoPath: assets.logos[footerLogo],
    clientLogoPath: assets.clientLogo,
    iconPath: (name) => {
      const found = assets.icons[name];
      if (!found) throw new AssetError(`internal: icon \`${name}\` was not copied`);
      return found;
    },
    dateLong: longDate(meta.date),
    buildStatus: intake?.buildStatus ?? 'final',
  };

  const coverViews = modules.flatMap((module) => module.output
    .filter((output) => output.type === 'cover')
    .map((output) => ({ module, output })));
  if (modules.length && coverViews.length !== 1) {
    throw new ContentError(`a guided template must select exactly one cover view, found ${coverViews.length}`);
  }
  const coverRenderer = coverViews.length
    ? moduleRenderers.get(`${coverViews[0].module.id}:${coverViews[0].output.id}`)
    : null;
  const html = renderDocument(renderedDoc, ctx, moduleRenderers, coverRenderer);
  writeFileSync(path.join(outDir, 'index.html'), html, 'utf8');

  // 4. A machine-readable record of what the build intended, so the validator
  //    checks the output against the content rather than against itself.
  const manifest = {
    generator: 'create-deliverables',
    archetype: archetype.name,
    accent: meta.accent,
    client: meta.client,
    title: meta.title,
    date: meta.date,
    classification: meta.classification,
    cover_surface: coverSurface,
    logo_variants: { cover: coverLogo, footer: footerLogo },
    icons: Object.keys(assets.icons),
    fonts: assets.fonts,
    bundle: Boolean(bundle),
    template_mode: modules.length ? 'guided' : 'legacy',
    build_status: intake?.buildStatus ?? 'final',
    required_question_count: intake?.answers.filter((answer) => answer.tier === 'required').length ?? 0,
    optional_question_count: intake?.answers.filter((answer) => answer.tier === 'optional').length ?? 0,
    unresolved_required_questions: intake?.requiredGaps.map((gap) => gap.id) ?? [],
    unresolved_optional_questions: intake?.optionalGaps.map((gap) => gap.id) ?? [],
    required_gaps_override_confirmed_at: intake?.overrideConfirmedAt ?? null,
    preview_module: previewModule,
  };
  writeFileSync(path.join(outDir, 'brand-manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');

  let bundlePath = null;
  if (bundle) bundlePath = writeBundle(outDir);

  return { outDir, html, manifest, assets, bundlePath, doc, renderedDoc, archetype, modules, intake };
}

function slugify(text) {
  return String(text).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'deliverable';
}

/* ==========================================================================
   CLI
   ========================================================================== */

async function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (err) {
    console.error(`\n  ${style.red('Error')}  ${err.message}${USAGE}`);
    process.exitCode = 1;
    return;
  }
  if (opts.help || !opts.content) {
    console.log(USAGE);
    return;
  }

  let result;
  try {
    result = await build(opts.content, opts);
  } catch (err) {
    if (err instanceof ContentError || err instanceof AssetError) return fatal(err);
    throw err;
  }

  const report = new Report(`Built ${result.manifest.title} — ${result.manifest.client}`, { summary: false });
  report.note(`output   ${path.relative(process.cwd(), result.outDir) || '.'}`);
  report.note(`archetype ${result.manifest.archetype} · accent ${result.manifest.accent}`);
  report.note(`sections ${result.doc.sections.length}`);
  if (result.intake) {
    report.note(`questions ${result.manifest.required_question_count} required · ${result.manifest.optional_question_count} optional`);
    report.note(`open      ${result.intake.requiredGaps.length} required · ${result.intake.optionalGaps.length} optional`);
  }
  if (result.manifest.preview_module) report.note(`preview   isolated module ${result.manifest.preview_module}`);
  if (result.bundlePath) {
    report.note(`bundle   ${path.relative(process.cwd(), result.bundlePath)} (open this one directly)`);
  }
  report.note(`preview  cd ${path.relative(process.cwd(), result.outDir) || '.'} && python3 -m http.server 8000`);
  report.print();

  if (result.intake?.requiredGaps.length) {
    console.log(`  ${style.yellow('Required information warning')}  ${result.intake.requiredGaps.length} required answers remain unresolved.`);
    for (const consequence of INCOMPLETE_CONSEQUENCES) console.log(`  ${style.yellow('WARN')} ${consequence}`);
    if (result.intake.buildStatus === 'final') {
      console.log(`  ${style.yellow('WARN')} The user explicitly confirmed a final build with required gaps at ${result.intake.overrideConfirmedAt}.`);
    }
    console.log('');
  }
  if (result.intake?.optionalGaps.length) {
    console.log(`  ${style.yellow('Optional information warning')}  ${result.intake.optionalGaps.length} optional answers were not provided. They are not rendered.`);
    console.log('');
  }

  if (!opts.validate) {
    console.log(`  ${style.yellow('The brand gate was skipped. Nothing here is cleared for a client.')}\n`);
    return;
  }

  // The gate runs automatically as the final step of every build.
  const gate = validateBuild(result.outDir);
  gate.print();
  if (!gate.ok) process.exitCode = 1;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => { fatal(err); process.exitCode = 1; });
}
