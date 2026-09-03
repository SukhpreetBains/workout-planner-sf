#!/usr/bin/env node
/** Rebuild and validate a detached custom microsite from its local source. */

import { cpSync, existsSync, readFileSync, rmSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';

import { ContentError } from './lib/content.mjs';
import { fatal, style } from './lib/report.mjs';
import { validateBuild } from './validate-brand.mjs';

export function rebuildDetached(packageDir, { out = null } = {}) {
  const root = path.resolve(packageDir);
  const manifestPath = path.join(root, 'detached.json');
  const sourceDir = path.join(root, 'src');
  if (!existsSync(manifestPath) || !existsSync(sourceDir)) {
    throw new ContentError(`\`${root}\` is not a detached deliverable package`);
  }
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  const outDir = path.resolve(out ?? path.join(root, 'dist'));
  if (existsSync(outDir)) rmSync(outDir, { recursive: true, force: true });
  cpSync(sourceDir, outDir, { recursive: true });
  const gate = validateBuild(outDir);
  return { outDir, manifest, gate };
}

function main() {
  const packageDir = process.argv[2];
  if (!packageDir) {
    console.error('Usage: node scripts/rebuild-detached.mjs <custom-source-dir>');
    process.exitCode = 1;
    return;
  }
  try {
    const result = rebuildDetached(packageDir);
    console.log(`\nCustom microsite rebuilt: ${result.outDir}`);
    if (result.manifest.unresolved_required_questions.length) {
      console.log(`  ${style.yellow('WARN')} ${result.manifest.unresolved_required_questions.length} required template questions were unresolved when this deliverable detached.`);
    }
    result.gate.print();
    if (!result.gate.ok) process.exitCode = 1;
  } catch (err) {
    if (err instanceof ContentError) return fatal(err);
    throw err;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) main();
