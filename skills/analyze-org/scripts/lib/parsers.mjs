// Offline gap-fill parsers over a retrieved force-app/ tree. These run regardless
// of API availability and are the sole source of edges in parse-only mode.
//
// v1 families:
//   1. Objects / fields / lookups / record types  (structural spine)
//   2. Apex class->class and trigger->handler/object
//   3. Flow targets + LWC -> FlexiPage placement
//   4. Permission sets / PSG access edges
//
// Path-derived ownership (objects/<Obj>/fields/...) is preferred over XML parsing
// where possible because it is unambiguous and robust.

import { readFileSync, readdirSync, existsSync } from 'node:fs'
import path from 'node:path'
import { XMLParser } from 'fast-xml-parser'
import { toArray } from './util.mjs'

const xml = new XMLParser({ ignoreAttributes: true, trimValues: true, parseTagValue: false })

function parseXmlFile(file) {
  try {
    const parsed = xml.parse(readFileSync(file, 'utf8'))
    const rootKey = Object.keys(parsed).find((k) => k !== '?xml')
    return rootKey ? parsed[rootKey] : null
  } catch {
    return null
  }
}

/** Recursively collect every value found under `key`, anywhere in the tree. */
function collectKey(node, key, acc = []) {
  if (node == null) return acc
  if (Array.isArray(node)) {
    for (const item of node) collectKey(item, key, acc)
    return acc
  }
  if (typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      if (k === key) for (const val of toArray(v)) acc.push(val)
      collectKey(v, key, acc)
    }
  }
  return acc
}

/** List all entries under root (recursive) as POSIX-style paths. Directories are
 *  included but harmless — they never match the metadata suffixes we test. */
function walk(root) {
  if (!existsSync(root)) return []
  return readdirSync(root, { recursive: true })
    .map((p) => path.join(root, p).split(path.sep).join('/'))
}

// Object name from a DX path segment ".../objects/<Obj>/...".
function objectFromPath(p) {
  const m = p.match(/\/objects\/([^/]+)\//)
  return m ? m[1] : null
}

// Basename minus a known metadata suffix.
function baseName(p, suffix) {
  return path.basename(p, suffix)
}

// ---------------------------------------------------------------------------
// Family 1 — objects / fields / lookups / record types
// ---------------------------------------------------------------------------
function parseObjects(graph, files, log) {
  let fields = 0, lookups = 0, rts = 0, vrs = 0
  for (const f of files) {
    if (f.endsWith('.object-meta.xml')) {
      const obj = baseName(f, '.object-meta.xml')
      graph.addNode('CustomObject', obj)
    } else if (f.includes('/fields/') && f.endsWith('.field-meta.xml')) {
      const obj = objectFromPath(f)
      if (!obj) continue
      const field = baseName(f, '.field-meta.xml')
      graph.addEdge('CustomObject', obj, 'CustomField', `${obj}.${field}`, 'object-owns-field')
      fields++
      const def = parseXmlFile(f)
      if (def) {
        for (const ref of toArray(def.referenceTo)) {
          if (ref && ref !== obj) {
            graph.addEdge('CustomObject', obj, 'CustomObject', ref, 'lookup')
            lookups++
          }
        }
      }
    } else if (f.includes('/recordTypes/') && f.endsWith('.recordType-meta.xml')) {
      const obj = objectFromPath(f)
      if (!obj) continue
      const rt = baseName(f, '.recordType-meta.xml')
      graph.addEdge('CustomObject', obj, 'RecordType', `${obj}.${rt}`, 'object-owns-recordtype')
      rts++
    } else if (f.includes('/validationRules/') && f.endsWith('.validationRule-meta.xml')) {
      const obj = objectFromPath(f)
      if (!obj) continue
      const vr = baseName(f, '.validationRule-meta.xml')
      graph.addEdge('CustomObject', obj, 'ValidationRule', `${obj}.${vr}`, 'object-owns-validationrule')
      vrs++
    }
  }
  log.info(`Parsed objects: ${fields} fields, ${lookups} lookups, ${rts} record types, ${vrs} validation rules.`)
}

// ---------------------------------------------------------------------------
// Family 2 — Apex class->class, trigger->object/handler
// ---------------------------------------------------------------------------
function stripApex(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, ' ') // block comments
    .replace(/\/\/[^\n]*/g, ' ')        // line comments
    .replace(/'(?:\\.|[^'\\])*'/g, ' ') // string literals
}

function parseApex(graph, files, log) {
  const classFiles = files.filter((f) => f.endsWith('.cls'))
  const triggerFiles = files.filter((f) => f.endsWith('.trigger'))
  const classNames = new Set(classFiles.map((f) => baseName(f, '.cls')))

  // Precompile a single matcher for all known class names (word-boundary).
  const names = [...classNames].filter((n) => n.length > 2)
  const matcher = names.length
    ? new RegExp(`\\b(${names.map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`, 'g')
    : null

  let classEdges = 0
  for (const f of classFiles) {
    const self = baseName(f, '.cls')
    if (!matcher) break
    const body = stripApex(readFileSync(f, 'utf8'))
    const refs = new Set()
    let m
    matcher.lastIndex = 0
    while ((m = matcher.exec(body))) if (m[1] !== self) refs.add(m[1])
    for (const ref of refs) {
      graph.addEdge('ApexClass', self, 'ApexClass', ref, 'apex-references-apex')
      classEdges++
    }
  }

  let triggerEdges = 0
  for (const f of triggerFiles) {
    const name = baseName(f, '.trigger')
    const raw = readFileSync(f, 'utf8')
    const onMatch = raw.match(/trigger\s+\w+\s+on\s+(\w+)/i)
    if (onMatch) {
      graph.addEdge('ApexTrigger', name, 'CustomObject', onMatch[1], 'trigger-on-object')
      triggerEdges++
    }
    if (matcher) {
      const body = stripApex(raw)
      const refs = new Set()
      let m
      matcher.lastIndex = 0
      while ((m = matcher.exec(body))) refs.add(m[1])
      for (const ref of refs) {
        graph.addEdge('ApexTrigger', name, 'ApexClass', ref, 'trigger-uses-handler')
        triggerEdges++
      }
    }
  }
  log.info(`Parsed apex: ${classEdges} class refs, ${triggerEdges} trigger edges (${classNames.size} classes, ${triggerFiles.length} triggers).`)
}

// ---------------------------------------------------------------------------
// Family 3 — Flow targets + LWC -> FlexiPage
// ---------------------------------------------------------------------------
function parseFlowsAndUi(graph, files, log) {
  let flowEdges = 0, pageEdges = 0

  // Register LWC bundles by directory name.
  for (const f of files) {
    const m = f.match(/\/lwc\/([^/]+)\/[^/]+\.js-meta\.xml$/)
    if (m) graph.addNode('LightningComponentBundle', m[1])
  }

  for (const f of files) {
    if (f.endsWith('.flow-meta.xml')) {
      const name = baseName(f, '.flow-meta.xml')
      const def = parseXmlFile(f)
      if (!def) continue
      const startObj = def.start?.object
      if (startObj) {
        graph.addEdge('Flow', name, 'CustomObject', startObj, 'flow-on-object')
        flowEdges++
      }
      for (const sub of collectKey(def.subflows, 'flowName')) {
        graph.addEdge('Flow', name, 'Flow', sub, 'flow-calls-subflow')
        flowEdges++
      }
      for (const call of toArray(def.actionCalls)) {
        if (call?.actionType === 'apex' && call.actionName) {
          graph.addEdge('Flow', name, 'ApexClass', call.actionName, 'flow-calls-apex')
          flowEdges++
        }
      }
    } else if (f.endsWith('.flexipage-meta.xml')) {
      const name = baseName(f, '.flexipage-meta.xml')
      const def = parseXmlFile(f)
      if (!def) continue
      if (def.sobjectType) {
        graph.addEdge('FlexiPage', name, 'CustomObject', def.sobjectType, 'flexipage-for-object')
        pageEdges++
      }
      for (const cn of collectKey(def, 'componentName')) {
        const lwc = typeof cn === 'string' && cn.startsWith('c:') ? cn.slice(2) : null
        if (lwc) {
          graph.addEdge('FlexiPage', name, 'LightningComponentBundle', lwc, 'flexipage-hosts-component')
          pageEdges++
        }
      }
    }
  }
  log.info(`Parsed flows/ui: ${flowEdges} flow edges, ${pageEdges} flexipage edges.`)
}

// ---------------------------------------------------------------------------
// Family 4 — Permission sets / PSG
// ---------------------------------------------------------------------------
function parsePermissions(graph, files, log) {
  let edges = 0
  for (const f of files) {
    if (f.endsWith('.permissionset-meta.xml')) {
      const name = baseName(f, '.permissionset-meta.xml')
      const def = parseXmlFile(f)
      if (!def) continue
      for (const op of toArray(def.objectPermissions)) {
        if (op?.object) { graph.addEdge('PermissionSet', name, 'CustomObject', op.object, 'permset-grants-object'); edges++ }
      }
      for (const fp of toArray(def.fieldPermissions)) {
        if (fp?.field) { graph.addEdge('PermissionSet', name, 'CustomField', fp.field, 'permset-grants-field'); edges++ }
      }
      for (const ca of toArray(def.classAccesses)) {
        if (ca?.apexClass) { graph.addEdge('PermissionSet', name, 'ApexClass', ca.apexClass, 'permset-grants-apex'); edges++ }
      }
      for (const ts of toArray(def.tabSettings)) {
        if (ts?.tab) { graph.addEdge('PermissionSet', name, 'CustomTab', ts.tab, 'permset-grants-tab'); edges++ }
      }
    } else if (f.endsWith('.permissionsetgroup-meta.xml')) {
      const name = baseName(f, '.permissionsetgroup-meta.xml')
      const def = parseXmlFile(f)
      if (!def) continue
      for (const ps of toArray(def.permissionSets)) {
        if (typeof ps === 'string') { graph.addEdge('PermissionSetGroup', name, 'PermissionSet', ps, 'psg-includes-permset'); edges++ }
      }
    }
  }
  log.info(`Parsed permissions: ${edges} access edges.`)
}

// Register a node for every discovered component so isolated ones (no edges)
// still appear in the inventory rather than vanishing.
function registerComponents(graph, files) {
  for (const f of files) {
    if (f.endsWith('.object-meta.xml')) graph.addNode('CustomObject', baseName(f, '.object-meta.xml'))
    else if (f.endsWith('.cls')) graph.addNode('ApexClass', baseName(f, '.cls'))
    else if (f.endsWith('.trigger')) graph.addNode('ApexTrigger', baseName(f, '.trigger'))
    else if (f.endsWith('.flow-meta.xml')) graph.addNode('Flow', baseName(f, '.flow-meta.xml'))
    else if (f.endsWith('.flexipage-meta.xml')) graph.addNode('FlexiPage', baseName(f, '.flexipage-meta.xml'))
    else if (f.endsWith('.permissionset-meta.xml')) graph.addNode('PermissionSet', baseName(f, '.permissionset-meta.xml'))
    else if (f.endsWith('.permissionsetgroup-meta.xml')) graph.addNode('PermissionSetGroup', baseName(f, '.permissionsetgroup-meta.xml'))
    else if (f.endsWith('.tab-meta.xml')) graph.addNode('CustomTab', baseName(f, '.tab-meta.xml'))
    else if (f.endsWith('.app-meta.xml')) graph.addNode('CustomApplication', baseName(f, '.app-meta.xml'))
  }
}

/** Run all parsers against the source tree, mutating the graph in place. */
export function parseLocalMetadata(graph, sourceDir, log) {
  const files = walk(sourceDir)
  log.info(`Scanning ${files.length} files under ${sourceDir}…`)
  registerComponents(graph, files)
  parseObjects(graph, files, log)
  parseApex(graph, files, log)
  parseFlowsAndUi(graph, files, log)
  parsePermissions(graph, files, log)
}
