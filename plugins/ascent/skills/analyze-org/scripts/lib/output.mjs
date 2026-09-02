// Emit artifacts to <outDir>: graph.json (LLM-consumable), clusters.json
// (suggested features, with names/notes preserved across refreshes), and
// graph.mmd (a cluster-level Mermaid view for humans to eyeball).

import { writeFileSync, mkdirSync, readFileSync, existsSync } from 'node:fs'
import path from 'node:path'

function readJsonIfExists(file) {
  try { return existsSync(file) ? JSON.parse(readFileSync(file, 'utf8')) : null } catch { return null }
}

// Human label for a cluster from its anchor id when no name was assigned yet.
function defaultName(anchorId) {
  const name = anchorId.split(':').slice(1).join(':') || anchorId
  return name
    .replace(/__(c|r|e|mdt|b|x)$/i, '')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function mermaidEsc(s) {
  return String(s).replace(/"/g, '\'').replace(/[\[\]{}<>|]/g, ' ')
}

export function writeArtifacts(outDir, graph, clustering, meta) {
  mkdirSync(outDir, { recursive: true })

  const graphJson = {
    generatedAt: meta.generatedAt,
    coverage: meta.coverage,                 // "full" | "reduced"
    source: meta.source,
    org: meta.org ?? null,
    stats: graph.stats(),
    nodes: [...graph.nodes.values()].map((n) => ({
      id: n.id, type: n.type, name: n.name, external: n.external, anchor: n.anchor,
      shared: clustering.shared.includes(n.id),
    })),
    edges: [...graph.edges.values()].map((e) => ({
      source: e.source, target: e.target, type: e.type, weight: e.weight,
    })),
  }
  writeFileSync(path.join(outDir, 'graph.json'), JSON.stringify(graphJson, null, 2))

  // --- clusters.json with refresh merge (preserve name + notes by stable id) --
  const prev = readJsonIfExists(path.join(outDir, 'clusters.json'))
  const prevById = new Map((prev?.clusters ?? []).map((c) => [c.id, c]))
  const prevIds = new Set(prevById.keys())
  const nowIds = new Set(clustering.clusters.map((c) => c.id))

  const clusters = clustering.clusters.map((c) => {
    const carried = prevById.get(c.id)
    return {
      id: c.id,
      name: carried?.name ?? defaultName(c.anchor),
      named: Boolean(carried?.name),           // false => LLM/human still needs to name it
      notes: carried?.notes ?? '',
      anchor: c.anchor,
      anchors: c.anchors,
      size: c.size,
      oversized: c.oversized,
      members: c.members,
      sharedRefs: c.sharedRefs,
    }
  })

  const drift = prev ? {
    added: [...nowIds].filter((id) => !prevIds.has(id)),
    removed: [...prevIds].filter((id) => !nowIds.has(id)),
  } : null

  const clustersJson = {
    generatedAt: meta.generatedAt,
    coverage: meta.coverage,
    summary: clustering.summary,
    drift,
    clusters,
    shared: clustering.shared,
    unclustered: clustering.unclustered,
  }
  writeFileSync(path.join(outDir, 'clusters.json'), JSON.stringify(clustersJson, null, 2))

  // --- graph.mmd: cluster-level summary view ---------------------------------
  writeFileSync(path.join(outDir, 'graph.mmd'), renderMermaid(graph, clusters, clustering))

  return { graphJson, clustersJson }
}

function renderMermaid(graph, clusters, clustering) {
  const memberToCluster = new Map()
  for (const c of clusters) for (const m of c.members) memberToCluster.set(m, c.id)
  const sharedSet = new Set(clustering.shared)

  // aggregate inter-cluster + cluster->shared weights
  const pair = new Map()          // "a|b" -> weight (a<b)
  const toShared = new Map()      // clusterId -> weight
  for (const e of graph.edges.values()) {
    if (graph.nodes.get(e.source)?.external || graph.nodes.get(e.target)?.external) continue
    const ca = memberToCluster.get(e.source)
    const cb = memberToCluster.get(e.target)
    const aShared = sharedSet.has(e.source)
    const bShared = sharedSet.has(e.target)
    if (ca && bShared) toShared.set(ca, (toShared.get(ca) || 0) + e.weight)
    else if (cb && aShared) toShared.set(cb, (toShared.get(cb) || 0) + e.weight)
    else if (ca && cb && ca !== cb) {
      const key = ca < cb ? `${ca}|${cb}` : `${cb}|${ca}`
      pair.set(key, (pair.get(key) || 0) + e.weight)
    }
  }

  const lines = ['graph LR']
  for (const c of clusters) {
    const tag = c.named ? c.name : `${c.name} *`
    lines.push(`  ${c.id}["${mermaidEsc(tag)}<br/>(${c.size})"]`)
  }
  if (clustering.shared.length) {
    lines.push(`  shared{{"Shared / Cross-cutting<br/>(${clustering.shared.length})"}}`)
  }
  for (const [key, w] of [...pair].sort((a, b) => b[1] - a[1])) {
    const [a, b] = key.split('|')
    lines.push(`  ${a} ---|${w}| ${b}`)
  }
  for (const [c, w] of [...toShared].sort((a, b) => b[1] - a[1])) {
    lines.push(`  ${c} -.->|${w}| shared`)
  }
  return lines.join('\n') + '\n'
}
