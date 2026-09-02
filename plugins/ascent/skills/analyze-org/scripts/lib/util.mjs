// Shared helpers: node identity, namespace detection, small utilities.

/** Canonical node id used everywhere: "<Type>:<Name>". */
export function nodeId(type, name) {
  return `${type}:${name}`
}

/** Coerce fast-xml-parser output (single value | array | undefined) into an array. */
export function toArray(v) {
  if (v === undefined || v === null) return []
  return Array.isArray(v) ? v : [v]
}

// Custom-suffix patterns that are NOT namespaces (they mark the kind of custom component).
const CUSTOM_SUFFIX = /(__c|__r|__e|__mdt|__b|__share|__history|__tag|__feed|__changeevent|__x|__pc|__pr|__kav|__ka)$/i

/**
 * Heuristic: is this API name a managed-package (namespaced) component?
 *
 * A namespace is always a *prefix* (`ns__Foo`), while a custom suffix is always
 * at the *end* (`Foo__c`). Names can be dotted (`Object.Field`), so we test each
 * segment: strip one trailing custom suffix, and if "__" still remains, the
 * leading token is a managed namespace prefix. Any namespaced segment => managed.
 */
export function isManaged(name) {
  if (!name || !name.includes('__')) return false
  return name.split('.').some((seg) => {
    if (!seg.includes('__')) return false
    return seg.replace(CUSTOM_SUFFIX, '').includes('__')
  })
}

/** Stable, dependency-free hash → short base36 string. Used for cluster ids. */
export function shortHash(str) {
  let h = 2166136261 >>> 0 // FNV-1a
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i)
    h = Math.imul(h, 16777619) >>> 0
  }
  return h.toString(36)
}

/** Slugify a name for human-readable labels / filenames. */
export function slug(s) {
  return String(s)
    .replace(/__(c|r|e|mdt|b|x)$/i, '')
    .replace(/[^a-zA-Z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase()
}

/** Console helpers that respect a quiet flag. */
export function makeLogger(quiet) {
  return {
    info: (...a) => { if (!quiet) console.error('[deps]', ...a) },
    warn: (...a) => console.error('[deps][WARN]', ...a),
    error: (...a) => console.error('[deps][ERROR]', ...a),
  }
}
