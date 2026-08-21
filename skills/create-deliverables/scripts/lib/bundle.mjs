/**
 * bundle.mjs — the `--bundle` single-file inliner.
 *
 * Produces `bundle.html`: one file, no external references, nothing left to
 * lose in transit. This is the artefact that survives being forwarded through
 * three inboxes, and it is also the only build output that can be opened
 * straight off disk — browsers refuse to fetch ES modules over `file://`, so
 * the folder build needs a local server while this one does not.
 *
 * The import map points `animejs` at a data URL, which is what lets the
 * inlined module resolve its import with no network and no file access.
 */

import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const MIME = {
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
};

function dataUrl(file) {
  const ext = path.extname(file).toLowerCase();
  const mime = MIME[ext];
  if (!mime) throw new Error(`bundle: no MIME type known for \`${ext}\``);
  return `data:${mime};base64,${readFileSync(file).toString('base64')}`;
}

/**
 * Inline every stylesheet, script, font and image referenced by index.html.
 *
 * @param {string} outDir a built deliverable directory
 * @returns {string} the path to bundle.html
 */
export function writeBundle(outDir) {
  const read = (rel) => readFileSync(path.join(outDir, rel), 'utf8');
  let html = read('index.html');

  // --- Stylesheets -------------------------------------------------------
  // Fonts inline as woff2 only. Every browser with import-map support has had
  // woff2 for years, and the woff fallback would double the payload of a file
  // that has to travel by email.
  html = html.replace(/[ \t]*<link rel="stylesheet" href="(css\/[a-z-]+\.css)">\n/g, (_, href) => {
    const css = read(href).replace(
      /url\("\.\.\/(fonts\/[a-z0-9-]+)\.woff2"\)\s*format\("woff2"\),\s*\n?\s*url\("\.\.\/fonts\/[a-z0-9-]+\.woff"\)\s*format\("woff"\)/g,
      (__, base) => `url("${dataUrl(path.join(outDir, `${base}.woff2`))}") format("woff2")`,
    );
    return `  <style data-from="${href}">\n${css}\n  </style>\n`;
  });

  // --- Anime.js, as the import map's target ------------------------------
  const anime = `data:text/javascript;base64,${readFileSync(path.join(outDir, 'js/anime.esm.min.js')).toString('base64')}`;
  html = html.replace(
    /<script type="importmap">[\s\S]*?<\/script>/,
    `<script type="importmap">{"imports":{"animejs":"${anime}"}}</script>`,
  );

  // --- The motion layer --------------------------------------------------
  const motion = read('js/motion.js');
  if (motion.includes('</script')) throw new Error('bundle: motion.js contains a closing script tag');
  html = html.replace(
    /[ \t]*<script type="module" src="js\/motion\.js"><\/script>/,
    `  <script type="module">\n${motion}\n  </script>`,
  );

  // --- Images ------------------------------------------------------------
  html = html.replace(/(\ssrc=")(assets\/[^"]+)(")/g, (_, before, rel, after) =>
    `${before}${dataUrl(path.join(outDir, rel))}${after}`);

  const bundlePath = path.join(outDir, 'bundle.html');
  writeFileSync(bundlePath, html, 'utf8');
  return bundlePath;
}
