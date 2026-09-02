#!/usr/bin/env node
/**
 * validate-brand.mjs — the delivery gate.
 *
 *   node scripts/validate-brand.mjs <built-dir>
 *
 * Walks a built deliverable's HTML, CSS and JS and checks it against the
 * Slalom brand, WCAG 2.1 AA, and the confidentiality rules that apply when
 * something leaves the building. Errors block delivery (exit 1); warnings
 * print and pass (exit 0). build.mjs runs this automatically as its last step.
 *
 * The allowed palette is parsed out of the built tokens.css at runtime, so the
 * palette has exactly one source of truth. The canonical brand values below
 * exist only to check that tokens.css itself has not drifted.
 *
 * These canonical values are Slalom's, not pack-aware: swapping the active
 * branding pack (branding/active.json in utilities-ui-generation) changes
 * which assets and docs this build reads, but every rule in this file still
 * checks against Slalom's exact palette, fonts, and copy. See the "Canonical
 * brand values" section below before deploying a non-Slalom pack.
 */

import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';

import { BRANDING, LOGO_FILES, SKILLS_DIR } from './lib/assets.mjs';
import { COLOR_BAR_ORDER } from './lib/components.mjs';
import { Report, fatal } from './lib/report.mjs';

/* ==========================================================================
   Canonical brand values (Slalom Brand Guide, February 2025)

   TODO(brand-packs): everything in this block — PALETTE, APPROVED_ON,
   SLALOM_BLUES, ACCENTS, DARK_3, SHIPPED_WEIGHTS — is hardcoded to Slalom's
   brand guide. Adding a client branding pack (see
   utilities-ui-generation/references/branding.md) does not make this file
   enforce that client's rules; it still validates every build against these
   exact values. Making the gate pack-aware means sourcing this block from
   the active pack (branding/packs/<pack>/) instead of literals here — e.g. a
   brand-rules.json alongside each pack's assets/ and docs/ — and threading
   that through every rule below that references PALETTE, APPROVED_ON, a
   Slalom-specific weight or copy check (rules 2-11, 15-19). Until then, this
   validator is Slalom-only regardless of which pack is active.
   ========================================================================== */

const PALETTE = {
  '#0C62FB': 'Slalom Blue',
  '#002FAF': 'Slalom Dark Blue',
  '#1BE1F2': 'Cyan',
  '#FF4D5F': 'Coral Red',
  '#C7B9FF': 'Purple',
  '#DEFF4D': 'Chartreuse',
  '#FFFFFF': 'White',
  '#E6E6E6': 'Light Gray',
  '#666666': 'Dark Gray',
  '#000000': 'Black',
  '#00BAD6': 'Cyan Dark 3', '#05C4DE': 'Cyan Dark 2', '#0ED3EB': 'Cyan Dark 1',
  '#5FEAF6': 'Cyan Light 1', '#8DF0F9': 'Cyan Light 2', '#D1F9FC': 'Cyan Light 3',
  '#E6154A': 'Coral Red Dark 3', '#F1214B': 'Coral Red Dark 2', '#F53958': 'Coral Red Dark 1',
  '#FF828F': 'Coral Red Light 1', '#FFA6AF': 'Coral Red Light 2', '#FFDBDF': 'Coral Red Light 3',
  '#9488F0': 'Purple Dark 3', '#A099F8': 'Purple Dark 2', '#B6ACF9': 'Purple Dark 1',
  '#D8CEFF': 'Purple Light 1', '#E3DCFF': 'Purple Light 2', '#F4F1FF': 'Purple Light 3',
  '#B3CC3E': 'Chartreuse Dark 3', '#BDDD07': 'Chartreuse Dark 2', '#CBEB0F': 'Chartreuse Dark 1',
  '#E8FF82': 'Chartreuse Light 1', '#EFFFA6': 'Chartreuse Light 2', '#F8FFDB': 'Chartreuse Light 3',
};

/** Approved text colours per background. */
const APPROVED_ON = {
  '#FFFFFF': ['#0C62FB', '#002FAF', '#000000', '#666666', '#E6154A'],
  '#0C62FB': ['#FFFFFF', '#DEFF4D', '#C7B9FF', '#1BE1F2'],
  '#000000': ['#FFFFFF', '#DEFF4D', '#C7B9FF', '#1BE1F2', '#FF4D5F'],
  '#1BE1F2': ['#002FAF', '#000000'],
  '#C7B9FF': ['#002FAF', '#000000'],
  '#DEFF4D': ['#002FAF', '#000000'],
  '#FF4D5F': ['#FFFFFF', '#000000'],
};

const SLALOM_BLUES = ['#0C62FB', '#002FAF'];
const ACCENTS = { cyan: '#1BE1F2', 'coral-red': '#FF4D5F', purple: '#C7B9FF', chartreuse: '#DEFF4D' };
const DARK_3 = { blue: '#002FAF', cyan: '#00BAD6', 'coral-red': '#E6154A', purple: '#9488F0', chartreuse: '#B3CC3E' };
const SHIPPED_WEIGHTS = [300, 400, 700, 900];

/** A hex literal, but not an anchor like `#s1-abcdef-thing`. */
const HEX_RE = /#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})(?![0-9a-zA-Z-])/g;

/* ==========================================================================
   Tiny CSS reader
   ========================================================================== */

/** Split stylesheet text into flat rules, descending through @media blocks. */
export function parseCss(css, at = []) {
  const rules = [];
  let i = 0;
  while (i < css.length) {
    const open = css.indexOf('{', i);
    if (open === -1) break;
    // The prelude runs from the previous rule's closing brace, so it carries
    // any comment written between the two. Strip it before reading a selector.
    const prelude = stripComments(css.slice(i, open)).trim();
    let depth = 1;
    let j = open + 1;
    while (j < css.length && depth > 0) {
      if (css[j] === '{') depth++;
      else if (css[j] === '}') depth--;
      j++;
    }
    const inner = css.slice(open + 1, j - 1);
    if (/^@(media|supports|layer|container)\b/.test(prelude)) {
      rules.push(...parseCss(inner, [...at, prelude]));
    } else {
      // A marker comment sits after the closing brace on the same line.
      const lineEnd = css.indexOf('\n', j);
      const trailer = css.slice(j, lineEnd === -1 ? css.length : lineEnd);
      rules.push({ selector: prelude, raw: inner, trailer, at });
    }
    i = j;
  }
  return rules;
}

function stripComments(text) {
  return text.replace(/\/\*[\s\S]*?\*\//g, ' ');
}

/** Declarations of a rule, plus whether it carries the `no-text` marker. */
export function declarations(rule) {
  const noText = /\/\*\s*no-text\s*\*\//.test(`${rule.raw}${rule.trailer ?? ''}`);
  const body = stripComments(rule.raw);
  const decls = [];
  let depth = 0;
  let buf = '';
  for (const ch of body) {
    if (ch === '(') depth++;
    else if (ch === ')') depth--;
    if (ch === ';' && depth === 0) { decls.push(buf); buf = ''; continue; }
    buf += ch;
  }
  decls.push(buf);
  const map = new Map();
  for (const decl of decls) {
    const at = decl.indexOf(':');
    if (at === -1) continue;
    const prop = decl.slice(0, at).trim();
    const value = decl.slice(at + 1).trim();
    if (prop && value) map.set(prop, value);
  }
  return { decls: map, noText };
}

/* ==========================================================================
   Tiny HTML reader
   ========================================================================== */

const VOID_TAGS = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
  'link', 'meta', 'param', 'source', 'track', 'wbr']);

/**
 * Flatten HTML into elements with their ancestor chain. Enough of a parser to
 * answer "what surface is this icon on" and "does this heading skip a level"
 * honestly, instead of guessing with a regex.
 */
export function parseHtml(html) {
  const elements = [];
  const stack = [];
  const tagRe = /<(\/?)([a-zA-Z][a-zA-Z0-9-]*)((?:[^>"']|"[^"]*"|'[^']*')*?)(\/?)>/g;
  let match;
  let cursor = 0;
  while ((match = tagRe.exec(html)) !== null) {
    const [full, closing, rawTag, rawAttrs, selfClose] = match;
    const tag = rawTag.toLowerCase();
    const text = html.slice(cursor, match.index);
    cursor = match.index + full.length;
    // Text belongs to every open element, not just the innermost one: "does
    // this severity indicator carry a word" is a question about the subtree.
    if (text.trim()) for (const open of stack) open.text += text;

    if (closing) {
      for (let i = stack.length - 1; i >= 0; i--) {
        if (stack[i].tag === tag) { stack.length = i; break; }
      }
      continue;
    }
    const el = {
      tag,
      attrs: parseAttrs(rawAttrs),
      parents: stack.map((s) => s),
      text: '',
      start: match.index,
      end: match.index + full.length,
    };
    elements.push(el);
    if (!VOID_TAGS.has(tag) && !selfClose) stack.push(el);
    // A comment or script body would confuse the stack; skip their contents.
    if (tag === 'script' || tag === 'style') {
      const close = html.toLowerCase().indexOf(`</${tag}>`, cursor);
      if (close !== -1) {
        el.text = html.slice(cursor, close);
        cursor = close + tag.length + 3;
        tagRe.lastIndex = cursor;
        stack.pop();
      }
    }
  }
  return elements;
}

function parseAttrs(raw) {
  const attrs = {};
  const re = /([a-zA-Z_:][a-zA-Z0-9_:.-]*)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?/g;
  let m;
  while ((m = re.exec(raw)) !== null) {
    attrs[m[1].toLowerCase()] = m[2] ?? m[3] ?? m[4] ?? '';
  }
  return attrs;
}

const classes = (el) => (el.attrs.class ?? '').split(/\s+/).filter(Boolean);
const hasClass = (el, name) => classes(el).includes(name);
const ancestors = (el) => [...el.parents].reverse();

function enclosingSurface(el) {
  for (const parent of [el, ...ancestors(el)]) {
    const found = classes(parent).find((c) => c.startsWith('surface-'));
    if (found) return found.slice('surface-'.length);
  }
  return null;
}

/* ==========================================================================
   Colour maths (WCAG 2.1 relative luminance)
   ========================================================================== */

export function hexToRgb(hex) {
  let h = hex.replace('#', '');
  if (h.length === 3) h = h.split('').map((c) => c + c).join('');
  if (h.length === 8) h = h.slice(0, 6);
  return [0, 2, 4].map((i) => Number.parseInt(h.slice(i, i + 2), 16));
}

export function luminance(hex) {
  const [r, g, b] = hexToRgb(hex).map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(a, b) {
  const la = luminance(a);
  const lb = luminance(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

/* ==========================================================================
   Token resolution
   ========================================================================== */

/** Read `--name: value` declarations out of tokens.css, per accent block. */
export function readTokens(tokensCss) {
  const root = new Map();
  const perAccent = new Map();
  for (const rule of parseCss(tokensCss)) {
    const { decls } = declarations(rule);
    const accentMatch = rule.selector.match(/^\[data-accent="([a-z-]+)"\]$/);
    const target = accentMatch ? (perAccent.get(accentMatch[1]) ?? new Map()) : root;
    for (const [prop, value] of decls) {
      if (prop.startsWith('--')) target.set(prop, value);
    }
    if (accentMatch) perAccent.set(accentMatch[1], target);
  }
  return { root, perAccent };
}

/** Resolve a token to a hex, following var() chains, for a given accent. */
export function resolveColor(tokens, name, accent, seen = new Set()) {
  if (seen.has(name)) return null;
  seen.add(name);
  const value = tokens.perAccent.get(accent)?.get(name) ?? tokens.root.get(name);
  if (!value) return null;
  const hex = value.match(/^#[0-9a-fA-F]{3,8}$/);
  if (hex) return hex[0].toUpperCase();
  const ref = value.match(/^var\(\s*(--[a-z0-9-]+)\s*\)$/i);
  if (ref) return resolveColor(tokens, ref[1], accent, seen);
  return null;
}

/** Resolve any CSS colour value (a token reference or a literal). */
function resolveValue(tokens, value, accent) {
  const ref = String(value).match(/var\(\s*(--[a-z0-9-]+)/i);
  if (ref) return resolveColor(tokens, ref[1], accent);
  const hex = String(value).match(/#[0-9a-fA-F]{3,8}/);
  return hex ? hex[0].toUpperCase() : null;
}

/* ==========================================================================
   File helpers
   ========================================================================== */

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, out);
    else out.push(full);
  }
  return out;
}

const TEXT_EXT = new Set(['.html', '.css', '.js', '.mjs', '.json', '.svg', '.md', '.txt']);

/* ==========================================================================
   The gate
   ========================================================================== */

export function validateBuild(dir) {
  const report = new Report(`Brand gate — ${path.basename(dir)}`);
  const abs = path.resolve(dir);

  const need = (rel) => {
    const full = path.join(abs, rel);
    if (!existsSync(full)) {
      report.error('structure', `\`${rel}\` is missing from the build`);
      return null;
    }
    return full;
  };

  const indexPath = need('index.html');
  const tokensPath = need('css/tokens.css');
  if (!indexPath || !tokensPath) return report;

  const files = walk(abs).map((f) => ({ abs: f, rel: path.relative(abs, f).split(path.sep).join('/') }));
  const read = (rel) => readFileSync(path.join(abs, rel), 'utf8');

  const html = read('index.html');
  const tokensCss = read('css/tokens.css');
  const tokens = readTokens(tokensCss);
  const elements = parseHtml(html);
  const root = elements.find((e) => e.tag === 'html');
  const accent = root?.attrs['data-accent'] ?? null;

  const manifestFile = files.find((f) => f.rel === 'brand-manifest.json');
  const manifest = manifestFile ? JSON.parse(readFileSync(manifestFile.abs, 'utf8')) : null;
  if (!manifest) report.note('no brand-manifest.json — content-dependent rules are checked against the HTML alone');

  // Stylesheets other than tokens.css, plus the motion layer: the files that
  // must contain no colour literal.
  const styleFiles = files.filter((f) => f.rel.startsWith('css/') && f.rel.endsWith('.css'));
  const authoredCss = styleFiles.filter((f) => f.rel !== 'css/tokens.css');
  const allCssText = styleFiles.map((f) => readFileSync(f.abs, 'utf8')).join('\n');
  const authoredRules = authoredCss.flatMap((f) =>
    parseCss(readFileSync(f.abs, 'utf8')).map((r) => ({ ...r, file: f.rel })));

  report.note(`accent ${accent ?? '(unset)'} · ${files.length} files`);

  /* --- Palette and composition ---------------------------------------- */

  // 1. No colour literal outside tokens.css.
  const literalTargets = files.filter((f) =>
    (f.rel.endsWith('.css') || f.rel === 'index.html' || f.rel === 'js/motion.js')
    && f.rel !== 'css/tokens.css');
  for (const file of literalTargets) {
    const text = readFileSync(file.abs, 'utf8');
    const hexes = [...text.matchAll(HEX_RE)].map((m) => m[0]);
    const functional = [...text.matchAll(/\b(?:rgba?|hsla?)\s*\(/g)].map((m) => m[0]);
    report.check(hexes.length === 0 && functional.length === 0, 'rule 1',
      `\`${file.rel}\` contains a colour literal (${[...hexes, ...functional].slice(0, 4).join(', ')}). `
      + 'Colour lives in tokens.css and nowhere else.');
  }

  // 2. Every hex in tokens.css is in the brand palette.
  const tokenHexes = [...new Set([...tokensCss.matchAll(HEX_RE)].map((m) => m[0].toUpperCase()))];
  const offPalette = tokenHexes.filter((h) => !(h in PALETTE));
  report.check(offPalette.length === 0, 'rule 2',
    `tokens.css declares off-palette colour${offPalette.length === 1 ? '' : 's'}: ${offPalette.join(', ')}`);
  report.check(tokenHexes.length > 0, 'rule 2', 'tokens.css declares no colours at all');

  // 3. Exactly one secondary accent in use, matching the content.
  report.check(accent !== null && accent in ACCENTS, 'rule 3',
    `<html data-accent> is \`${accent}\`, which is not one of ${Object.keys(ACCENTS).join(', ')}`);
  if (manifest) {
    report.check(accent === manifest.accent, 'rule 3',
      `<html data-accent="${accent}"> does not match meta.accent (\`${manifest.accent}\`)`);
  }
  const secondaryNames = Object.keys(ACCENTS);
  for (const rule of authoredRules) {
    const used = secondaryNames.filter((n) => new RegExp(`var\\(\\s*--${n}(?![a-z-])`).test(rule.raw));
    if (!used.length) continue;
    const isColorBar = /color-bar/.test(rule.selector);
    report.check(isColorBar, 'rule 3',
      `\`${rule.file}\` selector \`${rule.selector}\` names the secondary colour ${used.join(', ')} directly. `
      + 'Components use var(--accent); only the colour bar may name the palette.');
  }

  // 4. A Slalom Blue is present.
  const referenced = new Set([...allCssText.matchAll(/var\(\s*(--[a-z0-9-]+)/gi)].map((m) => m[1]));
  const bluePresent = [...referenced].some((name) => {
    const hex = resolveColor(tokens, name, accent);
    return hex && SLALOM_BLUES.includes(hex);
  });
  report.check(bluePresent, 'rule 4',
    'no Slalom Blue appears in the composition. A Slalom Blue is non-negotiable in every composition.');

  // 5. One colour bar, in the brand order, no more than 20% of the layout.
  const bars = elements.filter((e) => hasClass(e, 'color-bar'));
  report.check(bars.length <= 1, 'rule 5', `${bars.length} colour bars found. One bar per layout, never more.`);
  if (bars.length === 1) {
    const order = elements
      .filter((e) => hasClass(e, 'color-bar__swatch'))
      .map((e) => classes(e).find((c) => c.startsWith('color-bar__swatch--'))?.slice(19))
      .filter(Boolean);
    report.check(order.join(',') === COLOR_BAR_ORDER.join(','), 'rule 5',
      `the colour bar runs ${order.join(', ')}. The order is always ${COLOR_BAR_ORDER.join(', ')} and is never reordered.`);
  }
  const barHeight = lengthToPx(tokens.root.get('--color-bar-height'));
  const coverHeight = lengthToPx(tokens.root.get('--cover-min-height'));
  if (barHeight !== null && coverHeight !== null) {
    report.check(barHeight / coverHeight <= 0.2, 'rule 5',
      `the colour bar is ${Math.round((barHeight / coverHeight) * 100)}% of the cover. Never larger than 20%.`);
  }
  const barRule = authoredRules.find((r) => r.selector === '.color-bar');
  const barMax = barRule ? declarations(barRule).decls.get('max-height') : null;
  report.check(barMax !== null && Number.parseFloat(barMax) <= 20, 'rule 5',
    '`.color-bar` must cap itself with `max-height: 20%` or less');

  // 6. A swatch matching the background moves to its Dark 3 tone, alone.
  const barBg = bars[0]?.attrs['data-bar-bg']
    ?? elements.find((e) => e.attrs['data-bar-bg'])?.attrs['data-bar-bg']
    ?? null;
  if (barBg && barBg in DARK_3) {
    const overrides = authoredRules.filter((r) => r.selector.includes(`[data-bar-bg="${barBg}"]`));
    report.check(overrides.length === 1, 'rule 6',
      `the layout background is ${barBg}, so exactly one swatch override is expected; found ${overrides.length}`);
    for (const rule of overrides) {
      const { decls } = declarations(rule);
      const swatch = rule.selector.match(/\.color-bar__swatch--([a-z-]+)/)?.[1];
      report.check(swatch === barBg, 'rule 6',
        `the override changes the \`${swatch}\` swatch, but the background is ${barBg}. Change that swatch only.`);
      report.check(decls.size === 1 && decls.has('background'), 'rule 6',
        `the swatch override declares ${[...decls.keys()].join(', ')}. Change nothing but the background.`);
      const resolved = resolveValue(tokens, decls.get('background') ?? '', accent);
      report.check(resolved === DARK_3[barBg], 'rule 6',
        `the ${barBg} swatch resolves to ${resolved}, not its Dark 3 tone ${DARK_3[barBg]}`);
    }
  }

  // 7. No gradient on a decorative surface.
  for (const file of literalTargets) {
    const text = readFileSync(file.abs, 'utf8');
    const gradient = text.match(/\b(?:linear|radial|conic)-gradient\s*\(/);
    report.check(!gradient, 'rule 7',
      `\`${file.rel}\` uses ${gradient?.[0]}. Decorative gradients are off-brand.`);
  }

  /* --- Typography ------------------------------------------------------ */

  // 8. Slalom Sans first, only bundled weights, no synthesised weight.
  const fontStack = tokens.root.get('--font-sans') ?? '';
  report.check(/^"Slalom Sans"/.test(fontStack.trim()), 'rule 8',
    `the font stack starts with \`${fontStack.split(',')[0]?.trim()}\`; Slalom Sans is the primary web face`);
  report.check(/font-synthesis:\s*none/.test(allCssText), 'rule 8',
    'no `font-synthesis: none` declared. Slalom Sans has no Medium or SemiBold; the browser must not invent one.');

  const faceRules = styleFiles.flatMap((f) => parseCss(readFileSync(f.abs, 'utf8')))
    .filter((r) => r.selector === '@font-face');
  const declaredWeights = new Set();
  for (const face of faceRules) {
    const { decls } = declarations(face);
    const weight = Number.parseInt(decls.get('font-weight') ?? '', 10);
    declaredWeights.add(weight);
    report.check(SHIPPED_WEIGHTS.includes(weight), 'rule 8',
      `@font-face declares weight ${weight}, which is not a Slalom Sans weight (${SHIPPED_WEIGHTS.join(', ')})`);
  }
  report.check(faceRules.length > 0, 'rule 8', 'no @font-face declared — Slalom Sans is not self-hosted');

  const usedWeights = new Set();
  for (const rule of [...authoredRules, ...parseCss(tokensCss)]) {
    const { decls } = declarations(rule);
    const value = decls.get('font-weight');
    if (!value) continue;
    const direct = Number.parseInt(value, 10);
    if (Number.isFinite(direct)) usedWeights.add(direct);
    else if (/^(bold|bolder|lighter)$/.test(value.trim())) usedWeights.add(value.trim());
  }
  const badWeights = [...usedWeights].filter((w) => !SHIPPED_WEIGHTS.includes(w));
  report.check(badWeights.length === 0, 'rule 8',
    `weight${badWeights.length === 1 ? '' : 's'} ${badWeights.join(', ')} used but not shipped. `
    + `Slalom Sans has only ${SHIPPED_WEIGHTS.join(', ')}.`);

  // 9. No Avenir anywhere — a PowerPoint-only face must not leak to the web.
  for (const file of files.filter((f) => TEXT_EXT.has(path.extname(f.rel)))) {
    const text = readFileSync(file.abs, 'utf8');
    report.check(!/avenir/i.test(text), 'rule 9',
      `\`${file.rel}\` mentions Avenir. Avenir Next LT Pro is PowerPoint-only and must never appear in web output.`);
  }

  // 10. Sentence case; all caps only on eyebrow labels.
  for (const heading of elements.filter((e) => /^h[1-6]$/.test(e.tag))) {
    const text = decodeEntities(heading.text).replace(/\s+/g, ' ').trim();
    const letters = text.replace(/[^A-Za-z]/g, '');
    const shouty = letters.length > 3 && letters === letters.toUpperCase();
    report.check(!shouty || hasClass(heading, 'eyebrow'), 'rule 10',
      `<${heading.tag}> "${text.slice(0, 60)}" is set in capitals. Sentence case throughout; all caps only for short eyebrow labels.`);
  }
  for (const rule of authoredRules) {
    const { decls } = declarations(rule);
    if (decls.get('text-transform')?.trim() !== 'uppercase') continue;
    report.check(/--tracking-eyebrow/.test(decls.get('letter-spacing') ?? ''), 'rule 10',
      `\`${rule.selector}\` sets text-transform: uppercase without the eyebrow tracking. `
      + 'All caps is reserved for eyebrow labels, which are tracked out.');
  }

  // 11. Flush left. Never justified, never centred body copy.
  for (const rule of authoredRules) {
    const align = declarations(rule).decls.get('text-align')?.trim();
    if (!align) continue;
    report.check(align !== 'justify', 'rule 11', `\`${rule.selector}\` sets text-align: justify. Type is flush left, ragged right.`);
    report.check(align !== 'center', 'rule 11', `\`${rule.selector}\` centres text. Type is flush left, ragged right.`);
  }

  // 12. At most three type sizes per composition (warn).
  const sizeByClass = new Map();
  for (const rule of authoredRules) {
    const size = declarations(rule).decls.get('font-size');
    if (!size) continue;
    for (const part of rule.selector.split(',')) {
      const last = [...part.matchAll(/\.([a-z0-9_-]+)/gi)].pop();
      if (last) sizeByClass.set(last[1], size.trim());
    }
  }
  const compositions = elements.filter((e) =>
    e.tag === 'section' || hasClass(e, 'cover') || hasClass(e, 'footer'));
  const busy = [];
  for (const comp of compositions) {
    const within = elements.filter((e) => e.parents.includes(comp) || e === comp);
    const sizes = new Set(['body']); // inherited body size counts as one
    for (const el of within) {
      for (const c of classes(el)) if (sizeByClass.has(c)) sizes.add(sizeByClass.get(c));
    }
    if (sizes.size > 3) {
      busy.push(`${comp.attrs.id ?? classes(comp)[0]} (${sizes.size})`);
    }
  }
  report.check(busy.length === 0, 'rule 12',
    `${busy.length} composition${busy.length === 1 ? '' : 's'} use more than three type sizes: ${busy.join(', ')}. `
    + 'Expected for a scrolling web readout (headline, body, caption, eyebrow) — review rather than ignore. '
    + 'See references/layout-system.md.', { warn: true });

  /* --- Assets ----------------------------------------------------------- */

  // 13. The logo byte-matches one of the four approved files.
  const approvedLogos = Object.entries(LOGO_FILES).map(([variant, file]) => {
    const full = path.join(BRANDING, 'logos', file);
    return existsSync(full) ? { variant, bytes: readFileSync(full) } : null;
  }).filter(Boolean);
  const logoFiles = files.filter((f) => /assets\/logo-slalom-[a-z-]+\.svg$/.test(f.rel));
  report.check(logoFiles.length > 0, 'rule 13', 'no Slalom logo in the output');
  for (const file of logoFiles) {
    const bytes = readFileSync(file.abs);
    report.check(approvedLogos.some((l) => l.bytes.equals(bytes)), 'rule 13',
      `\`${file.rel}\` does not byte-match any approved logo in the active branding pack's assets/logos/. `
      + 'The mark is used unaltered — never recoloured or edited.');
  }

  // 14. Clear space at least the width of an "o"; height at least 9px.
  const logoHeight = lengthToPx(tokens.root.get('--logo-height'));
  report.check(logoHeight !== null && logoHeight >= 9, 'rule 14',
    `--logo-height resolves to ${logoHeight}px; the brand minimum is 9px`);
  const clearSpace = tokens.root.get('--logo-clear-space') ?? '';
  const factor = Number.parseFloat(clearSpace.match(/var\(--logo-height\)\s*\*\s*([\d.]+)/)?.[1] ?? 'NaN');
  report.check(Number.isFinite(factor) && factor >= 0.428, 'rule 14',
    `--logo-clear-space is \`${clearSpace}\`. Clear space must be at least the width of an "o" `
    + '(0.428 × the logo height on the 216 × 56.1 viewBox).');

  // 15. Every icon and illustration traces back to the active branding pack's assets.
  const brandAssetBytes = collectBrandAssets();
  for (const el of elements.filter((e) => e.tag === 'img')) {
    const src = el.attrs.src ?? '';
    if ('data-client-asset' in el.attrs) continue;      // the client's own mark
    if (!/^assets\//.test(src)) continue;               // handled by rules 22/23
    const full = path.join(abs, src);
    if (!existsSync(full)) { report.error('rule 15', `\`${src}\` is referenced but not in the output`); continue; }
    if (/logo-slalom/.test(src)) continue;              // rule 13 owns the logo
    const bytes = readFileSync(full);
    report.check(brandAssetBytes.some((b) => b.equals(bytes)), 'rule 15',
      `\`${src}\` does not match any approved asset in the active branding pack's assets/. `
      + 'Never invent an icon or illustration; use the approved library.');
  }

  // 16. Icons are never reversed, and never sit on a Slalom Blue circle.
  const circleClasses = new Set(authoredRules
    .filter((r) => /border-radius:\s*50%/.test(r.raw))
    .flatMap((r) => [...r.selector.matchAll(/\.([a-z0-9_-]+)/gi)].map((m) => m[1])));
  for (const el of elements.filter((e) => e.tag === 'img' && /assets\/icon-/.test(e.attrs.src ?? ''))) {
    const surface = enclosingSurface(el);
    report.check(surface === 'white' || surface === null, 'rule 16',
      `the icon \`${el.attrs.src}\` sits on the ${surface} surface. Icons are Slalom Blue and are never reversed light-on-dark.`);
    const onCircle = [el, ...ancestors(el)].some((p) => classes(p).some((c) => circleClasses.has(c)));
    report.check(!onCircle, 'rule 16',
      `the icon \`${el.attrs.src}\` sits on a circle. An icon on a circle is Slalom Dark Blue and the circle is never blue — check references/graphic-elements.md.`);
  }

  /* --- Accessibility ---------------------------------------------------- */

  // 17 + 18. Approved text-on-background pairs, and their contrast.
  const surfacePairs = [];
  for (const [name] of tokens.root) {
    const m = name.match(/^--on-([a-z-]+?)-(body|display|muted|emphasis)$/);
    if (!m) continue;
    const [, surface, role] = m;
    const accents = surface === 'accent' ? Object.keys(ACCENTS) : [accent ?? 'cyan'];
    for (const a of accents) {
      const bg = resolveColor(tokens, `--surface-${surface}-bg`, a);
      const fg = resolveColor(tokens, name, a);
      if (bg && fg) surfacePairs.push({ bg, fg, name, surface, role, accent: a });
    }
  }
  report.check(surfacePairs.length > 0, 'rule 17', 'tokens.css declares no surface/text pairs to check');
  for (const pair of surfacePairs) {
    const approved = APPROVED_ON[pair.bg] ?? [];
    report.check(approved.includes(pair.fg), 'rule 17',
      `${PALETTE[pair.fg] ?? pair.fg} on ${PALETTE[pair.bg] ?? pair.bg} (${pair.name}) is not an approved combination`);
    const ratio = contrast(pair.fg, pair.bg);
    const min = pair.role === 'display' ? 3 : 4.5;
    report.check(ratio >= min, 'rule 18',
      `${pair.name} on the ${pair.surface} surface is ${ratio.toFixed(2)}:1, below the ${min}:1 minimum`
      + `${pair.surface === 'accent' ? ` (accent: ${pair.accent})` : ''}`);
  }

  // Every authored rule that paints a background must pair an approved text
  // colour from the same surface, and every `color` must come from an --on-* token.
  for (const rule of authoredRules) {
    const { decls, noText } = declarations(rule);
    const bg = decls.get('background') ?? decls.get('background-color');
    const fg = decls.get('color');
    if (bg && !noText) {
      report.check(Boolean(fg), 'rule 17',
        `\`${rule.selector}\` in ${rule.file} paints a background without pairing a text colour. `
        + 'Pair one from the same surface, or mark the rule with a `no-text` comment.');
      if (fg) {
        const bgHex = resolveValue(tokens, bg, accent);
        const fgHex = resolveValue(tokens, fg, accent);
        if (bgHex && fgHex) {
          report.check((APPROVED_ON[bgHex] ?? []).includes(fgHex), 'rule 17',
            `\`${rule.selector}\` puts ${PALETTE[fgHex] ?? fgHex} on ${PALETTE[bgHex] ?? bgHex}, which is not approved`);
        }
      }
    }
    if (fg) {
      const ok = /var\(\s*--on-/.test(fg) || /^(currentColor|inherit|transparent)$/i.test(fg.trim());
      report.check(ok, 'rule 17',
        `\`${rule.selector}\` sets color to \`${fg}\`. Text colour comes from an --on-<surface>-* token so the pair stays checkable.`);
    }
  }

  // 19. Nothing conveys meaning by colour alone.
  const severities = elements.filter((e) => hasClass(e, 'severity'));
  for (const el of severities) {
    report.check(/\b(High|Medium|Low)\b/.test(decodeEntities(el.text)), 'rule 19',
      'a severity indicator carries no text label. Severity renders as a meter plus the word.');
  }
  const cells = elements.filter((e) => 'data-cell' in e.attrs);
  for (const cell of cells) {
    const within = elements.filter((e) => e.parents.includes(cell));
    report.check(within.some((e) => hasClass(e, 'cell__value')), 'rule 19',
      'a heatmap cell carries no printed value. Every cell prints its numeral.');
  }
  if (cells.length) {
    report.check(elements.some((e) => hasClass(e, 'heatmap__legend')), 'rule 19',
      'the heatmap has no legend. The scale must be spelled out.');
  }

  // 20. Accessible names, heading order, visible focus.
  for (const el of elements.filter((e) => e.tag === 'img')) {
    report.check('alt' in el.attrs, 'rule 20',
      `<img src="${el.attrs.src}"> has no alt attribute (use alt="" only when the image is decorative)`);
  }
  for (const el of elements.filter((e) => e.tag === 'svg')) {
    const named = el.attrs['aria-hidden'] === 'true' || 'aria-label' in el.attrs || /<title[\s>]/i.test(el.text);
    report.check(named, 'rule 20',
      'an inline <svg> has no accessible name and is not marked aria-hidden="true"');
  }
  let previousLevel = 0;
  for (const heading of elements.filter((e) => /^h[1-6]$/.test(e.tag))) {
    const level = Number(heading.tag[1]);
    report.check(previousLevel === 0 ? level === 1 : level <= previousLevel + 1, 'rule 20',
      `heading order jumps from h${previousLevel} to h${level} ("${decodeEntities(heading.text).trim().slice(0, 40)}")`);
    previousLevel = Math.max(previousLevel, level);
  }
  const focusRule = authoredRules.find((r) => r.selector.includes(':focus-visible') && /outline/.test(r.raw));
  report.check(Boolean(focusRule), 'rule 20', 'no visible :focus-visible outline is declared');
  if (focusRule) {
    report.check(!/outline:\s*(none|0)\b/.test(focusRule.raw), 'rule 20', ':focus-visible removes the outline');
  }

  // 21. Reduced motion resolves every animated element to its final state.
  const reducedRules = styleFiles.flatMap((f) => parseCss(readFileSync(f.abs, 'utf8')))
    .filter((r) => r.at.some((a) => /prefers-reduced-motion:\s*reduce/.test(a)));
  report.check(reducedRules.length > 0, 'rule 21',
    'no `prefers-reduced-motion: reduce` block. Reduced motion must apply final states, not merely skip animation.');
  const motionReset = reducedRules.find((r) => r.selector.includes('[data-motion]'));
  report.check(Boolean(motionReset), 'rule 21',
    'the reduced-motion block does not target `[data-motion]`, so animated elements keep whatever state they were left in');
  if (motionReset) {
    const { decls } = declarations(motionReset);
    report.check(/^1\b/.test(decls.get('opacity') ?? ''), 'rule 21',
      'the reduced-motion block does not force `opacity: 1`. This is how a page ends up permanently invisible.');
    report.check(/^none\b/.test(decls.get('transform') ?? ''), 'rule 21',
      'the reduced-motion block does not force `transform: none`');
  }
  report.check(reducedRules.some((r) => /stroke-dashoffset:\s*0/.test(r.raw)), 'rule 21',
    'the reduced-motion block does not reset `stroke-dashoffset`, so drawn lines stay undrawn');

  // Motion recipes exist for every declared data-motion value.
  const motionJs = existsSync(path.join(abs, 'js/motion.js')) ? read('js/motion.js') : '';
  const recipeNames = new Set([...motionJs.matchAll(/^ {2}'?([a-z-]+)'?:\s*\(/gm)].map((m) => m[1]));
  const declaredMotions = new Set(elements.map((e) => e.attrs['data-motion']).filter(Boolean));
  for (const name of declaredMotions) {
    report.check(recipeNames.has(name), 'rule 21',
      `data-motion="${name}" has no recipe in motion.js, so that element never animates or reveals`);
  }

  /* --- Delivery and confidentiality ------------------------------------ */

  // 22. Zero external references.
  for (const file of files.filter((f) => TEXT_EXT.has(path.extname(f.rel)) && f.rel !== 'js/LICENSE.md')) {
    const text = readFileSync(file.abs, 'utf8');
    const hits = externalReferences(text);
    report.check(hits.length === 0, 'rule 22',
      `\`${file.rel}\` makes an external reference: ${hits.slice(0, 3).join(', ')}. `
      + 'A client deliverable makes no network request — no CDN, no font service, no analytics, no tracking pixel.');
  }

  // 23. Relative asset paths only.
  for (const el of elements) {
    for (const attr of ['src', 'href']) {
      const value = el.attrs[attr];
      if (value === undefined || value === '') continue;
      if (value.startsWith('#')) continue;
      const bad = value.startsWith('/') || /^[a-z]+:/i.test(value) || /^[A-Za-z]:[\\/]/.test(value);
      report.check(!bad, 'rule 23',
        `<${el.tag} ${attr}="${value}"> is not a relative path. Everything a deliverable loads travels with it.`);
    }
  }
  report.check(!/url\(\s*["']?(?:\/|[a-z]+:)/i.test(allCssText.replace(/url\(\s*["']?data:/gi, 'url(data-')), 'rule 23',
    'a CSS url() uses an absolute path');

  // 24. The classification marker appears on the cover and in the footer.
  const classification = manifest?.classification
    ?? elements.find((e) => e.tag === 'meta' && e.attrs.name === 'classification')?.attrs.content
    ?? null;
  if (!classification) {
    report.error('rule 24', 'no classification found. Every client deliverable carries its confidentiality marker.');
  } else {
    const cover = elements.find((e) => hasClass(e, 'cover'));
    const footer = elements.find((e) => hasClass(e, 'footer'));
    for (const [label, container] of [['cover', cover], ['footer', footer]]) {
      const marks = elements.filter((e) =>
        hasClass(e, 'classification') && (e === container || e.parents.includes(container)));
      report.check(container && marks.some((m) => decodeEntities(m.text).includes(classification)), 'rule 24',
        `the classification "${classification}" does not appear on the ${label}`);
    }
  }

  // 25. print.css present, linked, and resolving animation to final state.
  const printLinked = elements.some((e) => e.tag === 'link' && (e.attrs.href ?? '').endsWith('print.css'));
  report.check(existsSync(path.join(abs, 'css/print.css')), 'rule 25', 'css/print.css is missing');
  report.check(printLinked, 'rule 25', 'css/print.css is not linked from index.html');
  if (existsSync(path.join(abs, 'css/print.css'))) {
    const printRules = parseCss(read('css/print.css')).filter((r) => r.at.some((a) => /@media\s+print/.test(a)));
    report.check(printRules.length > 0, 'rule 25', 'print.css has no @media print block');
    const reset = printRules.find((r) => r.selector.includes('[data-motion]'));
    report.check(Boolean(reset) && /opacity:\s*1/.test(reset?.raw ?? '') && /transform:\s*none/.test(reset?.raw ?? ''),
      'rule 25', 'print.css does not resolve animated elements to their final state');
  }

  // 26. Anime.js ships with its MIT licence.
  const hasAnime = existsSync(path.join(abs, 'js/anime.esm.min.js'));
  report.check(hasAnime, 'rule 26', 'js/anime.esm.min.js is missing');
  report.check(existsSync(path.join(abs, 'js/LICENSE.md')), 'rule 26',
    "Anime.js's LICENSE.md is not in the output. MIT requires the licence travel with the code.");

  // 27. No .otf; woff2 with a woff fallback.
  const otf = files.filter((f) => f.rel.endsWith('.otf'));
  report.check(otf.length === 0, 'rule 27',
    `desktop font file${otf.length === 1 ? '' : 's'} shipped: ${otf.map((f) => f.rel).join(', ')}. Never ship .otf on the web.`);
  for (const face of faceRules) {
    const { decls } = declarations(face);
    const src = decls.get('src') ?? '';
    const woff2 = src.match(/url\("([^"]+\.woff2)"\)/);
    const woff = src.match(/url\("([^"]+\.woff)"\)/);
    report.check(Boolean(woff2) && Boolean(woff), 'rule 27',
      `an @font-face is missing a ${woff2 ? 'woff fallback' : 'woff2 source'}`);
    for (const ref of [woff2?.[1], woff?.[1]].filter(Boolean)) {
      const resolved = path.normalize(path.join(abs, 'css', ref));
      report.check(existsSync(resolved), 'rule 27', `@font-face references \`${ref}\`, which is not in the output`);
    }
  }

  // 28. Shipping the Slalom Sans files is a licensing question of its own.
  const shippedFonts = files.filter((f) => /\.woff2?$/.test(f.rel));
  report.check(shippedFonts.length === 0, 'rule 28',
    `${shippedFonts.length} Slalom Sans font files are in the output. Slalom Sans is proprietary and licensed to `
    + 'Slalom: handing a client a folder that contains the font files is a redistribution question, and it is '
    + 'distinct from embedding the font in a PDF or hosting the site on Slalom infrastructure. Confirm before handoff.',
    { warn: true });

  /* --- Known brand deviations, surfaced rather than buried -------------- */

  if (elements.some((e) => hasClass(e, 'quote'))) {
    report.warn('deviation',
      'the quote uses a Slalom Sans–only treatment. Both approved pairings in typography.md want a supporting '
      + 'serif, and no serif ships with this repo, so neither can be fully satisfied. Disclose this if the '
      + 'deliverable is brand-reviewed.');
  }
  if (elements.some((e) => hasClass(e, 'slalom-line'))) {
    report.warn('deviation',
      'the Slalom line on the cover is drawn rather than taken from the Creative Library vector files. '
      + 'graphic-elements.md prefers the official vectors — swap it if the deliverable is going to a brand review.');
  }

  /* --- The bundle ------------------------------------------------------- */

  const bundlePath = path.join(abs, 'bundle.html');
  if (existsSync(bundlePath)) {
    const bundle = readFileSync(bundlePath, 'utf8');
    const hits = externalReferences(bundle);
    report.check(hits.length === 0, 'rule 22',
      `bundle.html makes an external reference: ${hits.slice(0, 3).join(', ')}`);
    report.check(!/<link\b[^>]*stylesheet/i.test(bundle), 'bundle',
      'bundle.html still links an external stylesheet, so it is not standalone');
    report.check(!/<script\b[^>]*\ssrc=/i.test(bundle), 'bundle',
      'bundle.html still loads a script by src, so it is not standalone');
  }

  return report;
}

/* ==========================================================================
   Helpers
   ========================================================================== */

function externalReferences(text) {
  const hits = [];
  const attrRe = /\b(?:src|href|poster|action|srcset)\s*=\s*["']\s*((?:https?:)?\/\/[^"']*)/gi;
  const urlRe = /url\(\s*["']?\s*((?:https?:)?\/\/[^"')]*)/gi;
  const importRe = /\bfrom\s*["']((?:https?:)?\/\/[^"']*)|\bimport\s*\(\s*["']((?:https?:)?\/\/[^"']*)/gi;
  for (const re of [attrRe, urlRe, importRe]) {
    for (const m of text.matchAll(re)) hits.push((m[1] ?? m[2]).slice(0, 60));
  }
  return [...new Set(hits)];
}

function lengthToPx(value) {
  if (!value) return null;
  const v = value.trim();
  const num = Number.parseFloat(v);
  if (!Number.isFinite(num)) return null;
  if (v.endsWith('rem') || v.endsWith('em')) return num * 16;
  if (v.endsWith('px')) return num;
  if (v.endsWith('vh')) return (num / 100) * 900;  // stated assumption: a 900px-tall viewport
  if (v.endsWith('vw')) return (num / 100) * 1440;
  return null;
}

function decodeEntities(text) {
  return String(text)
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'").replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&');
}

let brandAssetCache = null;
function collectBrandAssets() {
  if (brandAssetCache) return brandAssetCache;
  const dirs = ['iconography', 'illustrations', 'logos', 'color-bars'].map((d) => path.join(BRANDING, d));
  const bytes = [];
  for (const dir of dirs) {
    if (!existsSync(dir)) continue;
    for (const file of walk(dir)) {
      if (/\.(svg|png|jpg|jpeg)$/i.test(file)) bytes.push(readFileSync(file));
    }
  }
  brandAssetCache = bytes;
  return bytes;
}

/* ==========================================================================
   CLI
   ========================================================================== */

function main() {
  const dir = process.argv[2];
  if (!dir) {
    console.log('\n  node scripts/validate-brand.mjs <built-dir>\n');
    return;
  }
  if (!existsSync(dir)) return fatal(new Error(`\`${dir}\` does not exist`));
  const report = validateBuild(dir);
  report.print();
  if (!report.ok) process.exitCode = 1;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  try {
    main();
  } catch (err) {
    fatal(err);
  }
}

export { SKILLS_DIR };
