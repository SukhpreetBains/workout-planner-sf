#!/usr/bin/env node
import { loadTemplateOptions, copyTemplateOptions } from './lib/template-options.mjs';
/**
 * build.mjs — content in, static microsite out.
 *
 *   node scripts/build.mjs <content.yaml|.json> [options]
 *
 *   --out <dir>       output directory (default ./build/<client>-<archetype>)
 *   --intake <file>   question coverage and evidence record for modular templates
 *   --preview-module  isolate one module from its template's static example
 *   --preview-template render a template-owned static example with every module
 *   --bundle          also emit <deliverable-name>.html, everything inlined into one file
 *   --no-validate     skip the brand gate for iteration only
 *
 * The microsite is a pure function of the content file. Nobody hand-edits the
 * output: change the content and rebuild.
 */

import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

import { ContentError, parseContentFile, resolveSectionType, validSectionTypes, validateContent } from './lib/content.mjs';
import {
  INCOMPLETE_CONSEQUENCES, decorateContentWithGaps, loadAndEvaluateIntake, loadModuleRenderers,
  loadTemplateModules, resolveGuidedContent,
} from './lib/intake.mjs';
import {
  AssetError, SKILL_ROOT, copyAssets, copyOwnAssets, copyProfileAssets, listIconNames, logoVariantFor,
} from './lib/assets.mjs';
import {
  railLabel, renderFooter, renderRail, renderSection, sectionId,
} from './lib/page.mjs';
import { esc } from '../modules/shared/primitives.mjs';
import { composeStructurePreview } from './lib/examples.mjs';
import { Report, fatal, style } from './lib/report.mjs';
import { writeBundle } from './lib/bundle.mjs';
import { validateBuild } from './validate-brand.mjs';

/* ==========================================================================
   Arguments
   ========================================================================== */

function parseArgs(argv) {
  const opts = { content: null, out: null, intake: null, previewModule: null, previewTemplate: null, industry: null, bundle: false, validate: true };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--out') opts.out = argv[++i];
    else if (arg === '--intake') opts.intake = argv[++i];
    else if (arg === '--preview-module') opts.previewModule = argv[++i];
    else if (arg === '--preview-template') opts.previewTemplate = argv[++i];
    else if (arg === '--industry') opts.industry = argv[++i];
    else if (arg === '--bundle') opts.bundle = true;
    else if (arg === '--no-validate') opts.validate = false;
    else if (arg === '-h' || arg === '--help') opts.help = true;
    else if (arg.startsWith('-')) throw new Error(`unknown option \`${arg}\``);
    else if (!opts.content) opts.content = arg;
    else throw new Error(`unexpected argument \`${arg}\``);
  }
  if (opts.content === null && !opts.previewModule && !opts.previewTemplate && !opts.help) {
    throw new Error('give a content file, --preview-module <id>, or --preview-template <name>');
  }
  if (opts.industry && !opts.previewModule && !opts.previewTemplate) {
    throw new Error('--industry only applies to --preview-module or --preview-template');
  }
  return opts;
}

const USAGE = `
  node scripts/build.mjs <content.yaml|.json> [--intake <file>] [--preview-module <id>] [--out <dir>] [--bundle] [--no-validate]
  node scripts/build.mjs --preview-module <id> [--preview-template <name>] [--industry <id>] [--out <dir>] [--bundle]
  node scripts/build.mjs --preview-template <name> [--industry <id>] [--out <dir>] [--bundle]
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
  return loadTemplateOptions(manifest, path.dirname(file));
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
  if (typeof coverRenderer !== 'function') {
    throw new Error('internal: no module-owned cover renderer registered');
  }
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
  const unansweredCount = doc._unansweredRequiredCount ?? 0;
  const draftNotice = unansweredCount > 0
    ? `
    <aside class="draft-notice surface-white" role="status" aria-label="Incomplete draft">
      <div class="section__inner"><p>Draft: ${unansweredCount} required question${unansweredCount === 1 ? ' is' : 's are'} unanswered.</p></div>
    </aside>`
    : '';

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
  ${meta.layout === 'microsite' || sections.some((section) => section.layout === 'microsite') ? '<link rel="stylesheet" href="css/reference-layout.css">' : ''}
  <link rel="stylesheet" href="css/print.css">
  <script type="importmap">{"imports":{"animejs":"./js/anime.esm.min.js"}}</script>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <div class="page">${draftNotice}
${coverRenderer(meta, ctx)}
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
  out = null, intake: intakePath = null, previewModule = null, previewTemplate = null,
  bundle = false, structurePreview = false,
} = {}) {
  const absContent = path.resolve(contentPath);
  const contentDir = path.dirname(absContent);

  // 1. Parse, then resolve the archetype the content asks for, then validate
  //    against both the schema and that archetype's manifest.
  const raw = parseContentFile(absContent);
  const archetypeName = raw?.meta?.archetype;
  const archetype = previewModule && structurePreview
    ? isolatedArchetype(loadArchetype(archetypeName), previewModule)
    : loadArchetype(archetypeName);
  const modules = loadTemplateModules(archetype, SKILL_ROOT);
  const guidedRaw = resolveGuidedContent(raw, modules);
  const doc = validateContent(guidedRaw, { archetype, iconNames: listIconNames() });
  const { meta, sections } = doc;
  const moduleRenderers = await loadModuleRenderers(modules);
  const intake = modules.length && !structurePreview
    ? loadAndEvaluateIntake(intakePath, archetype, modules)
    : null;
  let renderedDoc = decorateContentWithGaps(doc, intake, modules);
  if (previewModule) {
    const previewDefinition = modules.find((module) => module.id === previewModule);
    if (!previewDefinition) {
      throw new ContentError(`preview module \`${previewModule}\` is not selected by this template`);
    }
    const previewSections = renderedDoc.sections.filter((section) => section.module === previewModule);
    const ownsBodyView = previewDefinition.output.some((output) => output.type !== 'cover');
    if (previewSections.length === 0 && ownsBodyView) {
      throw new ContentError(`content has no authored sections for preview module \`${previewModule}\``);
    }
    renderedDoc = { ...renderedDoc, sections: previewSections };
  }

  // 2. Work out which brand assets this particular deliverable needs.
  const coverSurface = archetype.cover_surface ?? 'blue';
  const coverLogo = logoVariantFor(coverSurface);
  const footerLogo = logoVariantFor(archetype.footer_surface ?? 'black');
  const icons = renderedDoc.sections.flatMap((s) =>
    resolveSectionType(s.type) === 'theme-group'
      ? (s.findings ?? []).map((f) => f.icon).filter(Boolean)
      : []);
  const clientLogo = meta.client_logo ? path.resolve(contentDir, meta.client_logo) : null;

  const outDir = path.resolve(out ?? path.join(
    process.cwd(), 'build',
    `${slugify(meta.client)}-${archetype.name}`));

  if (existsSync(outDir)) rmSync(outDir, { recursive: true, force: true });
  mkdirSync(outDir, { recursive: true });

  const assets = copyAssets(outDir, {
    logoVariants: [coverLogo, footerLogo, ...(archetype.cover_background_question ? ['blue'] : [])],
    icons,
    clientLogo,
  });
  copyOwnAssets(outDir, {
    referenceLayouts: meta.layout === 'microsite' || renderedDoc.sections.some((section) => section.layout === 'microsite'),
  });
  const templateAssets = copyTemplateOptions(archetype, intake, outDir);
  const profiles = copyProfileAssets(renderedDoc.sections, contentDir, outDir);

  // 3. Render.
  const ctx = {
    meta,
    ...templateAssets,
    profilePath: (name) => profiles[name],
    coverSurface,
    logoPath: assets.logos[templateAssets.coverBackground ? 'blue' : coverLogo],
    footerLogoPath: assets.logos[footerLogo],
    clientLogoPath: assets.clientLogo,
    iconPath: (name) => {
      const found = assets.icons[name];
      if (!found) throw new AssetError(`internal: icon \`${name}\` was not copied`);
      return found;
    },
    dateLong: longDate(meta.date),
    buildStatus: intake?.buildStatus ?? 'final',
    structurePreview,
    moduleTitles: new Map(modules.map((module) => [module.id, module.title])),
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
    logo_variants: { cover: templateAssets.coverBackground ? 'blue' : coverLogo, footer: footerLogo },
    icons: Object.keys(assets.icons),
    fonts: assets.fonts,
    bundle: Boolean(bundle),
    bundle_filename: bundle ? `${slugify(meta.title)}.html` : null,
    template_mode: modules.length ? 'guided' : 'legacy',
    build_status: intake?.buildStatus ?? 'final',
    required_question_count: intake?.answers.filter((answer) => answer.tier === 'required').length ?? 0,
    optional_question_count: intake?.answers.filter((answer) => answer.tier === 'optional').length ?? 0,
    unresolved_required_questions: intake?.requiredGaps.map((gap) => gap.id) ?? [],
    unresolved_optional_questions: intake?.optionalGaps.map((gap) => gap.id) ?? [],
    required_gaps_override_confirmed_at: intake?.overrideConfirmedAt ?? null,
    preview_module: previewModule,
    preview_template: previewTemplate,
  };
  writeFileSync(path.join(outDir, 'brand-manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');

  let bundlePath = null;
  if (bundle) bundlePath = writeBundle(outDir, manifest.bundle_filename);

  return { outDir, html, manifest, assets, bundlePath, doc, renderedDoc, archetype, modules, intake };
}

function templatesContainingModule(moduleId) {
  const templatesRoot = path.join(SKILL_ROOT, 'templates');
  return readdirSync(templatesRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .filter((name) => {
      const file = path.join(templatesRoot, name, 'archetype.json');
      if (!existsSync(file)) return false;
      const manifest = JSON.parse(readFileSync(file, 'utf8'));
      return (manifest.modules ?? []).some((entry) => (typeof entry === 'string' ? entry : entry.id) === moduleId);
    });
}

/** Isolated review includes every owned view, regardless of template selection. */
function isolatedArchetype(archetype, moduleId) {
  return { ...archetype, allowed_sections: validSectionTypes(), required_sections: [],
    modules: archetype.modules.map((entry) => (typeof entry === 'string' ? entry : entry.id) === moduleId ? { id: moduleId } : entry),
  };
}

export async function buildStructurePreview({
  moduleId = null, templateName = null, industry = null, out = null, bundle = false,
} = {}) {
  let resolvedTemplate = templateName;
  if (!resolvedTemplate && moduleId) {
    const candidates = templatesContainingModule(moduleId);
    if (candidates.length === 0) throw new ContentError(`no template selects module \`${moduleId}\``);
    resolvedTemplate = candidates.includes('project-kickoff') ? 'project-kickoff' : candidates[0];
  }
  const archetype = moduleId ? isolatedArchetype(loadArchetype(resolvedTemplate), moduleId) : loadArchetype(resolvedTemplate);
  const modules = loadTemplateModules(archetype, SKILL_ROOT);
  const raw = composeStructurePreview(archetype, modules, SKILL_ROOT, { previewModule: moduleId, industry });
  const tempDir = mkdtempSync(path.join(os.tmpdir(), 'create-deliverables-preview-'));
  const contentPath = path.join(tempDir, 'content.json');
  writeFileSync(contentPath, `${JSON.stringify(raw, null, 2)}\n`, 'utf8');
  try {
    return await build(contentPath, {
      out,
      previewModule: moduleId,
      previewTemplate: resolvedTemplate,
      bundle,
      structurePreview: true,
    });
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
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
  if (opts.help) {
    console.log(USAGE);
    return;
  }

  let result;
  try {
    result = opts.content
      ? await build(opts.content, opts)
      : await buildStructurePreview({
          moduleId: opts.previewModule,
          templateName: opts.previewTemplate,
          industry: opts.industry,
          out: opts.out,
          bundle: opts.bundle,
        });
  } catch (err) {
    if (err instanceof ContentError || err instanceof AssetError) return fatal(err);
    throw err;
  }

  const report = new Report(`Built ${result.manifest.title} — ${result.manifest.client}`, { summary: false });
  report.note(`output   ${path.relative(process.cwd(), result.outDir) || '.'}`);
  report.note(`archetype ${result.manifest.archetype} · accent ${result.manifest.accent}`);
  report.note(`sections ${result.renderedDoc.sections.length}`);
  if (result.intake) {
    report.note(`questions ${result.manifest.required_question_count} required · ${result.manifest.optional_question_count} optional`);
    report.note(`open      ${result.intake.requiredGaps.length} required · ${result.intake.optionalGaps.length} optional`);
  }
  if (result.manifest.preview_module) report.note(`preview   isolated module ${result.manifest.preview_module}`);
  else if (result.manifest.preview_template) report.note(`preview   all modules in template ${result.manifest.preview_template}`);
  if (result.bundlePath) {
    report.note(`bundle   ${path.relative(process.cwd(), result.bundlePath)} (open this one directly)`);
  }
  report.note(`preview  cd ${path.relative(process.cwd(), result.outDir) || '.'} && python3 -m http.server 8000`);
  report.print();
  if (result.archetype.instructionsText && opts.previewTemplate) console.log(`\nTemplate custom instructions:\n${result.archetype.instructionsText}`);
  if (result.archetype.template_questions?.length) console.log(`Visual choices: ${path.join(result.outDir, 'template-choices.html')}`);

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
