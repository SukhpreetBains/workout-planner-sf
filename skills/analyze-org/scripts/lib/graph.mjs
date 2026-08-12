// In-memory graph: a node registry + a deduped, weighted edge list, plus
// adjacency for the clusterer. No external graph library — the clustering we
// use (object-anchored, weighted label propagation) is custom anyway.

import { nodeId, isManaged } from './util.mjs'
import { weightFor } from './weights.mjs'

// Types that can anchor a feature cluster.
const ANCHOR_TYPES = new Set(['CustomObject', 'CustomApplication'])

export class Graph {
  constructor() {
    this.nodes = new Map()   // id -> { id, type, name, external, anchor }
    this.edges = new Map()   // "src|tgt|type" -> { source, target, type, weight }
  }

  /** Register (or upgrade) a node. Returns its id. */
  addNode(type, name) {
    if (!type || !name) return null
    const id = nodeId(type, name)
    if (!this.nodes.has(id)) {
      this.nodes.set(id, {
        id,
        type,
        name,
        external: isManaged(name),
        anchor: ANCHOR_TYPES.has(type) && !isManaged(name),
      })
    }
    return id
  }

  /**
   * Add a typed edge. Endpoints are auto-registered if unseen (with the given
   * type). Self-loops are ignored. Duplicate (src,tgt,type) edges are merged.
   */
  addEdge(srcType, srcName, tgtType, tgtName, edgeType) {
    const source = this.addNode(srcType, srcName)
    const target = this.addNode(tgtType, tgtName)
    if (!source || !target || source === target) return
    const key = `${source}|${target}|${edgeType}`
    if (!this.edges.has(key)) {
      this.edges.set(key, { source, target, type: edgeType, weight: weightFor(edgeType) })
    }
  }

  /** All anchor node ids (custom objects + apps, unmanaged). */
  anchors() {
    return [...this.nodes.values()].filter((n) => n.anchor).map((n) => n.id)
  }

  /**
   * Undirected weighted adjacency, managed nodes excluded as *members* but their
   * edges preserved so callers can still see external dependencies separately.
   * Returns Map<nodeId, Map<neighborId, summedWeight>> over non-external nodes.
   */
  adjacency() {
    const adj = new Map()
    const internal = (id) => this.nodes.get(id) && !this.nodes.get(id).external
    const ensure = (id) => {
      if (!adj.has(id)) adj.set(id, new Map())
      return adj.get(id)
    }
    for (const e of this.edges.values()) {
      if (!internal(e.source) || !internal(e.target)) continue
      ensure(e.source).set(e.target, (ensure(e.source).get(e.target) || 0) + e.weight)
      ensure(e.target).set(e.source, (ensure(e.target).get(e.source) || 0) + e.weight)
    }
    // Make sure every internal node appears, even isolated ones.
    for (const n of this.nodes.values()) if (!n.external) ensure(n.id)
    return adj
  }

  stats() {
    let external = 0
    for (const n of this.nodes.values()) if (n.external) external++
    return {
      nodes: this.nodes.size,
      externalNodes: external,
      edges: this.edges.size,
      anchors: this.anchors().length,
    }
  }
}
