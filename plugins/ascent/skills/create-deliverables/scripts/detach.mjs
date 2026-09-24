#!/usr/bin/env node
/** Turn a generated microsite into an isolated, editable source package. */

import {
  cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync,
} from 'node:fs';
import path from 'node:path';
import process from 'node:process';

import { ContentError } from './lib/content.mjs';
import { fatal } from './lib/report.mjs';

export function detachBuild(buildDir, outDir, { confirmIncomplete = false } = {}) {
  const sourceBuild = path.resolve(buildDir);
  const destination = path.resolve(outDir);
  const buildManifestPath = path.join(sourceBuild, 'brand-manifest.json');
  if (!existsSync(buildManifestPath)) throw new ContentError(`no brand-manifest.json found in \`${sourceBuild}\``);
  const buildManifest = JSON.parse(readFileSync(buildManifestPath, 'utf8'));
  if (buildManifest.generator !== 'create-deliverables') throw new ContentError('the source is not a create-deliverables build');
  const gaps = buildManifest.unresolved_required_questions ?? [];
  if (gaps.length && !confirmIncomplete) {
    throw new ContentError(
      `the build has ${gaps.length} unresolved required questions. Detach only after warning the user, then pass --confirm-incomplete`);
  }
  if (existsSync(destination)) throw new ContentError(`detach destination already exists: \`${destination}\``);

  const sourceDir = path.join(destination, 'src');
  mkdirSync(destination, { recursive: true });
  cpSync(sourceBuild, sourceDir, { recursive: true });
  const staleBundle = buildManifest.bundle_filename
    ? path.join(sourceDir, buildManifest.bundle_filename)
    : path.join(sourceDir, 'bundle.html');
  if (existsSync(staleBundle)) rmSync(staleBundle);

  const detachedAt = new Date().toISOString();
  const detachedManifest = {
    schema_version: 1,
    mode: 'detached',
    source_template: buildManifest.archetype,
    detached_at: detachedAt,
    source_build: sourceBuild,
    unresolved_required_questions: gaps,
    safety_gates: ['brand', 'accessibility', 'confidentiality', 'no-external-requests'],
  };
  writeFileSync(path.join(destination, 'detached.json'), `${JSON.stringify(detachedManifest, null, 2)}\n`);
  writeFileSync(path.join(sourceDir, 'brand-manifest.json'), `${JSON.stringify({
    ...buildManifest,
    template_mode: 'detached',
    bundle: false,
    detached_at: detachedAt,
  }, null, 2)}\n`);
  return { destination, sourceDir, manifest: detachedManifest };
}

function main() {
  const args = process.argv.slice(2);
  const buildDir = args[0];
  const outIndex = args.indexOf('--out');
  const outDir = outIndex >= 0 ? args[outIndex + 1] : null;
  const confirmIncomplete = args.includes('--confirm-incomplete');
  if (!buildDir || !outDir) {
    console.error('Usage: node scripts/detach.mjs <built-dir> --out <custom-source-dir> [--confirm-incomplete]');
    process.exitCode = 1;
    return;
  }
  try {
    const result = detachBuild(buildDir, outDir, { confirmIncomplete });
    console.log(`Detached editable source: ${result.sourceDir}`);
    console.log(`Rebuild with: node scripts/rebuild-detached.mjs ${result.destination}`);
  } catch (err) {
    if (err instanceof ContentError) return fatal(err);
    throw err;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) main();
