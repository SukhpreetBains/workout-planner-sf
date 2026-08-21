/**
 * yaml.mjs — a bounded YAML subset parser. Zero dependencies.
 *
 * Node has no built-in YAML parser and this skill takes no npm dependencies.
 * Rather than approximate the full spec badly, this parser supports an
 * explicitly enumerated subset and REFUSES everything else with a line number.
 * Mis-parsing a client deliverable's content is worse than failing to parse it.
 *
 * Supported
 *   - two-space-indented nested mappings and sequences
 *   - plain, single-quoted and double-quoted scalars
 *   - block scalars: `|` `|-` `>` `>-`
 *   - inline flow sequences: [a, b, c]
 *   - `#` comments and blank lines
 *   - true/false/null/integer/float coercion; everything else stays a string
 *
 * Refused (errors, never guessed at)
 *   anchors/aliases (& *), multiple documents (---), tags (!!),
 *   complex keys (?), flow mappings ({}), tab indentation, odd indentation
 */

export class YamlError extends Error {
  constructor(message, line) {
    super(line ? `line ${line}: ${message}` : message);
    this.name = 'YamlError';
    this.line = line ?? null;
  }
}

const KEY_RE = /^([A-Za-z_][A-Za-z0-9_-]*)\s*:(?:[ \t]+(.*))?$/;

/** Strip an unquoted trailing `#` comment. Returns the code portion. */
function stripComment(text) {
  let quote = null;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quote) {
      if (c === quote) quote = null;
      else if (quote === '"' && c === '\\') i++;
    } else if (c === '"' || c === "'") {
      quote = c;
    } else if (c === '#' && (i === 0 || /\s/.test(text[i - 1]))) {
      return text.slice(0, i);
    }
  }
  return text;
}

function refuseUnsupported(content, lineNo) {
  const t = content.trim();
  if (t === '---' || t.startsWith('--- ')) {
    throw new YamlError('document markers (`---`) are not supported; use a single document', lineNo);
  }
  if (t === '...') throw new YamlError('document end marker (`...`) is not supported', lineNo);
  if (t.startsWith('? ')) throw new YamlError('complex keys (`?`) are not supported', lineNo);
  if (t.startsWith('%')) throw new YamlError('directives (`%`) are not supported', lineNo);
  // `key:value` would otherwise fall through and be read as the plain scalar
  // "key:value" — a silent mis-parse. The `//` exclusion keeps URLs working.
  if (/^[A-Za-z_][A-Za-z0-9_-]*:(?!\/\/)\S/.test(t)) {
    throw new YamlError(`malformed key (a colon must be followed by a space): \`${t}\``, lineNo);
  }
}

function refuseUnsupportedValue(value, lineNo) {
  const t = value.trim();
  if (!t) return;
  if (t.startsWith('&')) throw new YamlError('anchors (`&`) are not supported', lineNo);
  if (t.startsWith('*')) throw new YamlError('aliases (`*`) are not supported', lineNo);
  if (t.startsWith('!')) throw new YamlError('tags (`!`) are not supported', lineNo);
  if (t.startsWith('{')) throw new YamlError('flow mappings (`{}`) are not supported; use an indented mapping', lineNo);
}

/**
 * Pass 1 — raw text to logical lines.
 * Splits `- item` into a bare `-` marker plus an item line at the item's own
 * column, so that pass 2 sees exactly one shape for every sequence. Block
 * scalars are consumed here so that `#` and blank lines inside them survive.
 */
function lex(text) {
  const raw = text.replace(/\r\n?/g, '\n').split('\n');
  const out = [];

  for (let i = 0; i < raw.length; i++) {
    const rawLine = raw[i];
    const lineNo = i + 1;

    if (/^\s*$/.test(rawLine)) continue;
    if (/^[ ]*\t/.test(rawLine) || /^\t/.test(rawLine)) {
      throw new YamlError('tab indentation is not supported; use two spaces per level', lineNo);
    }

    const code = stripComment(rawLine);
    if (/^\s*$/.test(code)) continue; // whole-line comment

    let indent = code.length - code.trimStart().length;
    let content = code.trimStart().trimEnd();

    refuseUnsupported(content, lineNo);

    // Split leading sequence markers. `- - a` is refused rather than guessed.
    while (content === '-' || content.startsWith('- ')) {
      out.push({ indent, content: '-', line: lineNo });
      if (content === '-') { content = ''; break; }
      const rest = content.slice(2);
      const shift = 2 + (rest.length - rest.trimStart().length);
      indent += shift;
      content = rest.trimStart();
      if (content === '-' || content.startsWith('- ')) {
        throw new YamlError('nested inline sequences (`- - x`) are not supported', lineNo);
      }
    }
    if (content === '') continue; // bare marker; its block follows on later lines

    // A block scalar header ends a logical line and swallows the raw lines below.
    const m = content.match(KEY_RE);
    const headerValue = m ? (m[2] ?? '') : content;
    const bs = headerValue.trim().match(/^([|>])([-+]?)$/);
    if (bs) {
      const [, style, chomp] = bs;
      if (chomp === '+') throw new YamlError('the `+` keep indicator is not supported', lineNo);
      if (!m) throw new YamlError('a block scalar must be the value of a key', lineNo);
      const body = [];
      let j = i + 1;
      let blockIndent = null;
      for (; j < raw.length; j++) {
        const l = raw[j];
        if (/^\s*$/.test(l)) { body.push(''); continue; }
        if (/^[ ]*\t/.test(l)) {
          throw new YamlError('tab indentation is not supported; use two spaces per level', j + 1);
        }
        const ind = l.length - l.trimStart().length;
        if (blockIndent === null) {
          if (ind <= indent) break;
          blockIndent = ind;
        }
        if (ind < blockIndent) break;
        body.push(l.slice(blockIndent));
      }
      if (blockIndent === null) {
        throw new YamlError(`block scalar \`${style}\` has no indented content`, lineNo);
      }
      while (body.length && body[body.length - 1] === '') body.pop();
      let value;
      if (style === '|') {
        value = body.join('\n');
      } else {
        // Folded: blank lines become newlines, adjacent non-blank lines join
        // with a space. A line indented further than the block keeps its break.
        value = '';
        for (const line of body) {
          if (line === '') { value += '\n'; continue; }
          if (value && !value.endsWith('\n')) value += /^\s/.test(line) ? '\n' : ' ';
          value += line;
        }
      }
      if (chomp !== '-') value += '\n';

      out.push({ indent, content: `${m[1]}:`, line: lineNo, key: m[1], block: value });
      i = j - 1;
      continue;
    }

    out.push({ indent, content, line: lineNo });
  }

  return out;
}

function parseFlowSequence(text, lineNo) {
  const inner = text.slice(1, -1);
  const items = [];
  let buf = '';
  let quote = null;
  for (let i = 0; i < inner.length; i++) {
    const c = inner[i];
    if (quote) {
      buf += c;
      if (c === quote) quote = null;
      else if (quote === '"' && c === '\\') buf += inner[++i] ?? '';
    } else if (c === '"' || c === "'") {
      quote = c; buf += c;
    } else if (c === ',') {
      items.push(buf); buf = '';
    } else if (c === '[' || c === ']') {
      throw new YamlError('nested flow sequences are not supported', lineNo);
    } else if (c === '{' || c === '}') {
      throw new YamlError('flow mappings (`{}`) are not supported', lineNo);
    } else {
      buf += c;
    }
  }
  if (quote) throw new YamlError('unterminated quoted string', lineNo);
  if (buf.trim() !== '' || items.length) items.push(buf);
  return items.map((s) => parseScalar(s.trim(), lineNo));
}

function parseScalar(text, lineNo) {
  refuseUnsupportedValue(text, lineNo);
  const t = text.trim();
  if (t === '') return null;

  if (t.startsWith('[')) {
    if (!t.endsWith(']')) throw new YamlError('unterminated flow sequence', lineNo);
    return parseFlowSequence(t, lineNo);
  }
  if (t.startsWith("'")) {
    if (t.length < 2 || !t.endsWith("'")) throw new YamlError('unterminated single-quoted string', lineNo);
    return t.slice(1, -1).replace(/''/g, "'");
  }
  if (t.startsWith('"')) {
    if (t.length < 2 || !t.endsWith('"')) throw new YamlError('unterminated double-quoted string', lineNo);
    return t.slice(1, -1).replace(/\\(.)/g, (_, c) =>
      ({ n: '\n', t: '\t', r: '\r', '"': '"', '\\': '\\', '/': '/' }[c] ?? c));
  }

  if (t === 'true') return true;
  if (t === 'false') return false;
  if (t === 'null' || t === '~') return null;
  if (/^-?\d+$/.test(t)) return Number.parseInt(t, 10);
  if (/^-?(?:\d+\.\d*|\.\d+)$/.test(t)) return Number.parseFloat(t);
  return t;
}

/** Pass 2 — logical lines to a JS value. */
function parseBlock(lines, start, indent) {
  const first = lines[start];
  if (first.content === '-') return parseSequence(lines, start, indent);
  if (first.key !== undefined && first.key !== null) return parseMapping(lines, start, indent);
  if (KEY_RE.test(first.content)) return parseMapping(lines, start, indent);

  // A lone scalar block.
  const value = parseScalar(first.content, first.line);
  const next = lines[start + 1];
  if (next && next.indent >= indent) {
    throw new YamlError(`unexpected content after the scalar on line ${first.line}`, next.line);
  }
  return [value, start + 1];
}

function childIndent(lines, i, indent, ownerLine) {
  const next = lines[i];
  if (!next || next.indent <= indent) return null;
  if (next.content === '-') {
    // A sequence may sit at the parent's indent or one level in; the lexer has
    // already normalised markers to their own column, so accept indent + 2.
    if (next.indent !== indent + 2) {
      throw new YamlError(
        `expected an indent of ${indent + 2} spaces for the block opened on line ${ownerLine}, found ${next.indent}`,
        next.line);
    }
    return next.indent;
  }
  if (next.indent !== indent + 2) {
    throw new YamlError(
      `expected an indent of ${indent + 2} spaces for the block opened on line ${ownerLine}, found ${next.indent}`,
      next.line);
  }
  return next.indent;
}

function parseMapping(lines, start, indent) {
  const map = {};
  let i = start;
  while (i < lines.length) {
    const line = lines[i];
    if (line.indent < indent) break;
    if (line.indent > indent) {
      throw new YamlError(`unexpected indentation (expected ${indent} spaces, found ${line.indent})`, line.line);
    }
    if (line.content === '-') {
      throw new YamlError('a sequence item cannot appear where a mapping key is expected', line.line);
    }

    // Block scalar: the lexer already resolved the value.
    if (line.block !== undefined) {
      if (!line.key) throw new YamlError('a block scalar must be the value of a key', line.line);
      if (line.key in map) throw new YamlError(`duplicate key \`${line.key}\``, line.line);
      map[line.key] = line.block;
      i++;
      continue;
    }

    const m = line.content.match(KEY_RE);
    if (!m) {
      if (line.content.includes(':')) {
        throw new YamlError(`malformed key (a colon must be followed by a space): \`${line.content}\``, line.line);
      }
      throw new YamlError(`expected \`key: value\`, found \`${line.content}\``, line.line);
    }
    const [, key, rawValue] = m;
    if (key in map) throw new YamlError(`duplicate key \`${key}\``, line.line);

    if (rawValue !== undefined && rawValue.trim() !== '') {
      map[key] = parseScalar(rawValue, line.line);
      i++;
      const next = lines[i];
      if (next && next.indent > indent) {
        throw new YamlError(`\`${key}\` already has an inline value, so it cannot also have an indented block`, next.line);
      }
      continue;
    }

    i++;
    const ci = childIndent(lines, i, indent, line.line);
    if (ci === null) {
      map[key] = null;
      continue;
    }
    const [value, next] = parseBlock(lines, i, ci);
    map[key] = value;
    i = next;
  }
  return [map, i];
}

function parseSequence(lines, start, indent) {
  const items = [];
  let i = start;
  while (i < lines.length) {
    const line = lines[i];
    if (line.indent < indent) break;
    if (line.indent > indent) {
      throw new YamlError(`unexpected indentation (expected ${indent} spaces, found ${line.indent})`, line.line);
    }
    if (line.content !== '-') {
      throw new YamlError(`expected a sequence item (\`- \`), found \`${line.content}\``, line.line);
    }
    i++;
    const ci = childIndent(lines, i, indent, line.line);
    if (ci === null) {
      items.push(null);
      continue;
    }
    const [value, next] = parseBlock(lines, i, ci);
    items.push(value);
    i = next;
  }
  return [items, i];
}

/**
 * Parse a YAML subset document. Throws YamlError with a line number on
 * anything outside the supported subset.
 */
export function parseYaml(text) {
  const lines = lex(text);
  if (lines.length === 0) return null;
  const baseIndent = lines[0].indent;
  if (baseIndent !== 0) throw new YamlError('the document must start at column 0', lines[0].line);
  const [value, end] = parseBlock(lines, 0, 0);
  if (end < lines.length) {
    throw new YamlError(`unexpected content after the end of the document`, lines[end].line);
  }
  return value;
}
