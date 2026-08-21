/**
 * assets.mjs — resolve and copy the sibling skills' assets into the output.
 *
 * Assets are COPIED, never symlinked: a built deliverable has to be
 * self-contained enough to zip, email, or drop on SharePoint. A missing logo or
 * font is a hard failure — silently emitting a deliverable with a broken mark
 * is the one outcome worse than not building at all.
 */

import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const SKILL_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const SKILLS_DIR = path.resolve(SKILL_ROOT, '..');

export const BRANDING = path.join(SKILLS_DIR, 'slalom-branding', 'assets');
export const ANIME_VENDOR = path.join(SKILLS_DIR, 'animejs', 'assets', 'vendor');

const WEBFONT_DIR = path.join(BRANDING, 'fonts', 'slalom-sans', 'Webfont Files');
const ICON_DIR = path.join(BRANDING, 'iconography');
const LOGO_DIR = path.join(BRANDING, 'logos');

export class AssetError extends Error {
  constructor(message) {
    super(message);
    this.name = 'AssetError';
  }
}

function require_(file, what) {
  if (!existsSync(file)) {
    throw new AssetError(
      `${what} is missing.\n  expected: ${file}\n  ` +
      `This skill depends on its sibling skills' assets. Check that ` +
      `${path.relative(SKILLS_DIR, file)} exists under ${SKILLS_DIR}.`);
  }
  return file;
}

/**
 * Slalom Sans, flattened to space-free filenames. The source directories
 * contain spaces ("Webfont Files"), which would force %20 into the CSS.
 * Only the four weights the kit declares are shipped; .otf never is.
 */
export const FONTS = [
  { out: 'slalom-sans-light', src: 'SlalomSans-Light', weight: 300 },
  { out: 'slalom-sans-regular', src: 'SlalomSans-Regular', weight: 400 },
  { out: 'slalom-sans-bold', src: 'SlalomSans-Bold', weight: 700 },
  { out: 'slalom-sans-black', src: 'SlalomSans-Black', weight: 900 },
];

export const LOGO_FILES = {
  blue: 'slalom-logo-blue-RGB.svg',
  'dark-blue': 'slalom-logo-dark-blue-RGB.svg',
  white: 'slalom-logo-white-RGB.svg',
  black: 'slalom-logo-black-RGB.svg',
};

/**
 * The logo variant approved against a given surface. A dark or saturated
 * surface takes the white mark; a light one takes the blue mark.
 */
export function logoVariantFor(surface) {
  switch (surface) {
    case 'blue':
    case 'black':
    case 'dark-blue':
      return 'white';
    case 'white':
    case 'light':
    case 'accent':
      return 'blue';
    default:
      throw new AssetError(`no approved logo variant for the \`${surface}\` surface`);
  }
}

/** Every approved icon name, for validating `finding.icon` at content time. */
export function listIconNames() {
  require_(ICON_DIR, 'the approved icon library');
  return new Set(
    readdirSync(ICON_DIR)
      .filter((f) => f.endsWith('.svg'))
      .map((f) => path.basename(f, '.svg')),
  );
}

function ensureDir(dir) {
  mkdirSync(dir, { recursive: true });
  return dir;
}

function copy(src, dest) {
  ensureDir(path.dirname(dest));
  copyFileSync(src, dest);
  return dest;
}

/**
 * Copy everything a built deliverable needs.
 *
 * @param {string} outDir             the build output directory
 * @param {object} plan
 * @param {string[]} plan.logoVariants  logo variants in use, e.g. ['white']
 * @param {string[]} plan.icons         icon names in use
 * @param {string|null} plan.clientLogo absolute path to the client's mark
 * @returns {{fonts: string[], logos: Record<string,string>, icons: Record<string,string>, clientLogo: string|null, anime: string, license: string}}
 */
export function copyAssets(outDir, plan) {
  const result = { fonts: [], logos: {}, icons: {}, clientLogo: null, anime: '', license: '' };

  // --- Fonts ------------------------------------------------------------
  require_(WEBFONT_DIR, 'the Slalom Sans webfont directory');
  for (const font of FONTS) {
    for (const ext of ['woff2', 'woff']) {
      const src = require_(path.join(WEBFONT_DIR, `${font.src}.${ext}`), `Slalom Sans ${font.src}.${ext}`);
      copy(src, path.join(outDir, 'fonts', `${font.out}.${ext}`));
      result.fonts.push(`fonts/${font.out}.${ext}`);
    }
  }

  // --- Logos ------------------------------------------------------------
  for (const variant of new Set(plan.logoVariants)) {
    const file = LOGO_FILES[variant];
    if (!file) throw new AssetError(`\`${variant}\` is not one of the four approved logo colours`);
    const src = require_(path.join(LOGO_DIR, file), `the ${variant} Slalom logo`);
    const out = `assets/logo-slalom-${variant}.svg`;
    copy(src, path.join(outDir, out));
    result.logos[variant] = out;
  }

  // --- Icons ------------------------------------------------------------
  for (const name of new Set(plan.icons)) {
    const src = path.join(ICON_DIR, `${name}.svg`);
    if (!existsSync(src)) {
      throw new AssetError(
        `\`${name}\` is not an approved icon.\n  expected: ${src}\n  ` +
        `Pick one from ${path.relative(SKILLS_DIR, ICON_DIR)} — never draw a new one.`);
    }
    const out = `assets/icon-${name}.svg`;
    copy(src, path.join(outDir, out));
    result.icons[name] = out;
  }

  // --- Client mark ------------------------------------------------------
  if (plan.clientLogo) {
    if (!existsSync(plan.clientLogo)) {
      throw new AssetError(`the client logo \`${plan.clientLogo}\` does not exist (meta.client_logo is relative to the content file)`);
    }
    const ext = path.extname(plan.clientLogo).toLowerCase();
    if (!['.svg', '.png'].includes(ext)) {
      throw new AssetError(`the client logo must be .svg or .png, found \`${ext}\``);
    }
    const out = `assets/client-logo${ext}`;
    copy(plan.clientLogo, path.join(outDir, out));
    result.clientLogo = out;
  }

  // --- Anime.js ---------------------------------------------------------
  // MIT requires the licence travel with the code. It ships next to the bundle,
  // always, and the validator treats its absence as an error.
  const anime = require_(path.join(ANIME_VENDOR, 'anime.esm.min.js'), 'the vendored Anime.js bundle');
  copy(anime, path.join(outDir, 'js', 'anime.esm.min.js'));
  result.anime = 'js/anime.esm.min.js';

  const license = require_(path.join(ANIME_VENDOR, 'LICENSE.md'), "Anime.js's MIT licence");
  copy(license, path.join(outDir, 'js', 'LICENSE.md'));
  result.license = 'js/LICENSE.md';

  return result;
}

/** Copy this skill's own stylesheets and motion layer. */
export function copyOwnAssets(outDir) {
  const css = ['tokens.css', 'base.css', 'components.css', 'print.css'];
  for (const file of css) {
    copy(require_(path.join(SKILL_ROOT, 'assets', 'css', file), `this skill's ${file}`),
      path.join(outDir, 'css', file));
  }
  copy(require_(path.join(SKILL_ROOT, 'assets', 'js', 'motion.js'), "this skill's motion.js"),
    path.join(outDir, 'js', 'motion.js'));
  return { css: css.map((f) => `css/${f}`), js: 'js/motion.js' };
}

export { ensureDir, readFileSync, writeFileSync, statSync, existsSync, require_ as requireFile };
