// Backbone edges from the Tooling API's MetadataComponentDependency object.
// A row means: MetadataComponent (source) depends on RefMetadataComponent (target).
//
// This is the most authoritative source, but coverage is incomplete for some
// metadata types and the object must be queryable in the org. On any failure we
// return null so the caller degrades to parse-only and flags reduced coverage.

import { execFileSync } from 'node:child_process'

const QUERY = [
  'SELECT MetadataComponentName, MetadataComponentType,',
  '       RefMetadataComponentName, RefMetadataComponentType',
  'FROM MetadataComponentDependency',
].join(' ')

/**
 * @returns {{records: Array}|null} records, or null if the API is unavailable.
 */
export function fetchApiDependencies(org, log) {
  if (!org) {
    log.warn('No --org provided; skipping MetadataComponentDependency API (parse-only).')
    return null
  }
  try {
    log.info(`Querying MetadataComponentDependency from org "${org}"…`)
    const sfBin = process.platform === 'win32' ? 'sf.cmd' : 'sf'
    const out = execFileSync(
      sfBin,
      ['data', 'query', '--query', QUERY, '--use-tooling-api', '--target-org', org, '--json'],
      { encoding: 'utf8', maxBuffer: 256 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'] },
    )
    const parsed = JSON.parse(out)
    const records = parsed?.result?.records ?? []
    if (!records.length) {
      log.warn('MetadataComponentDependency returned 0 rows — degrading to parse-only.')
      return null
    }
    log.info(`API returned ${records.length} dependency rows.`)
    return { records }
  } catch (err) {
    const msg = (err.stderr || err.stdout || err.message || '').toString().trim().split('\n')[0]
    log.warn(`MetadataComponentDependency query failed (${msg}). Degrading to parse-only.`)
    return null
  }
}

/** Map API dependency rows into graph edges. */
export function applyApiEdges(graph, records, log) {
  let applied = 0
  for (const r of records) {
    const sType = r.MetadataComponentType
    const sName = r.MetadataComponentName
    const tType = r.RefMetadataComponentType
    const tName = r.RefMetadataComponentName
    if (!sType || !sName || !tType || !tName) continue
    graph.addEdge(sType, sName, tType, tName, 'api-dependency')
    applied++
  }
  log.info(`Applied ${applied} API edges.`)
}
