// Object-anchored, weighted feature clustering.
//
// 1. Seed one cluster per anchor (custom object / app).
// 2. Propagate labels outward: each non-anchor node joins the cluster it is most
//    strongly connected to (sum of edge weights to already-labelled neighbors).
// 3. Float high fan-in "shared" nodes (referenced by >= sharedThreshold clusters)
//    into a Shared / Cross-cutting group so a utility never merges two features.
// 4. Guardrails: merge sub-minimum clusters into their strongest neighbor and cap
//    the total at maxFeatures; flag (don't force-split) oversized clusters.
// 5. Assign stable ids hashed from each cluster's primary anchor.

import { shortHash } from './util.mjs'

const MAX_ITERATIONS = 25

export function cluster(graph, opts = {}) {
  const sharedThreshold = opts.sharedThreshold ?? 3
  const maxFeatures = opts.maxFeatures ?? 15
  const minSize = opts.minSize ?? 3

  const adj = graph.adjacency()
  const anchorIds = new Set(graph.anchors())

  // --- 1 & 2: seed + propagate ------------------------------------------------
  const label = new Map()                 // nodeId -> clusterKey (anchor id) | null
  for (const id of adj.keys()) label.set(id, anchorIds.has(id) ? id : null)

  const movable = [...adj.keys()].filter((id) => !anchorIds.has(id)).sort()
  for (let iter = 0; iter < MAX_ITERATIONS; iter++) {
    let changed = false
    for (const id of movable) {
      const scores = new Map()
      for (const [nbr, w] of adj.get(id)) {
        const lab = label.get(nbr)
        if (lab) scores.set(lab, (scores.get(lab) || 0) + w)
      }
      if (!scores.size) continue
      // argmax weight, deterministic tie-break by cluster key.
      let best = null, bestW = -1
      for (const [k, w] of [...scores].sort((a, b) => a[0] < b[0] ? -1 : 1)) {
        if (w > bestW) { best = k; bestW = w }
      }
      if (label.get(id) !== best) { label.set(id, best); changed = true }
    }
    if (!changed) break
  }

  // --- 3: float shared nodes --------------------------------------------------
  const shared = new Set()
  for (const id of movable) {
    if (!label.get(id)) continue
    const clustersTouched = new Set()
    for (const nbr of adj.get(id).keys()) {
      const lab = label.get(nbr)
      if (lab) clustersTouched.add(lab)
    }
    if (clustersTouched.size >= sharedThreshold) shared.add(id)
  }
  for (const id of shared) label.set(id, null) // remove from feature membership

  // --- assemble clusters ------------------------------------------------------
  // clusterKey -> { anchors:Set, members:Set }
  const clusters = new Map()
  const nodeToCluster = new Map()
  const ensure = (key) => {
    if (!clusters.has(key)) clusters.set(key, { anchors: new Set(), members: new Set() })
    return clusters.get(key)
  }
  for (const id of anchorIds) { ensure(id).anchors.add(id); ensure(id).members.add(id); nodeToCluster.set(id, id) }
  for (const id of movable) {
    const k = label.get(id)
    if (!k) continue
    ensure(k).members.add(id)
    nodeToCluster.set(id, k)
  }

  const interWeight = () => {
    // keyA -> keyB -> summed crossing weight
    const w = new Map()
    const bump = (a, b, v) => {
      if (!w.has(a)) w.set(a, new Map())
      w.get(a).set(b, (w.get(a).get(b) || 0) + v)
    }
    for (const [id, nbrs] of adj) {
      const ka = nodeToCluster.get(id)
      if (!ka) continue
      for (const [nbr, wt] of nbrs) {
        const kb = nodeToCluster.get(nbr)
        if (!kb || kb === ka) continue
        bump(ka, kb, wt)
      }
    }
    return w
  }

  const merge = (into, from) => {
    const a = clusters.get(into), b = clusters.get(from)
    for (const m of b.members) { a.members.add(m); nodeToCluster.set(m, into) }
    for (const an of b.anchors) a.anchors.add(an)
    clusters.delete(from)
  }

  const strongestNeighbor = (key, weights) => {
    const row = weights.get(key)
    if (!row || !row.size) return null
    let best = null, bestW = -1
    for (const [k, w] of [...row].sort((a, b) => a[0] < b[0] ? -1 : 1)) {
      if (w > bestW) { best = k; bestW = w }
    }
    return best
  }

  // --- 4a: merge sub-minimum clusters ----------------------------------------
  let mergedTiny = 0
  let progress = true
  while (progress) {
    progress = false
    const weights = interWeight()
    const tiny = [...clusters].filter(([, c]) => c.members.size < minSize).sort((a, b) => a[1].members.size - b[1].members.size)
    for (const [key] of tiny) {
      if (!clusters.has(key)) continue
      const target = strongestNeighbor(key, weights)
      if (target && clusters.has(target)) { merge(target, key); mergedTiny++; progress = true; break }
    }
  }

  // --- 4b: cap to maxFeatures -------------------------------------------------
  let mergedCap = 0
  while (clusters.size > maxFeatures) {
    const weights = interWeight()
    // Prefer merging the most strongly-connected pair; else fold the two smallest.
    let pair = null, pairW = -1
    for (const [a, row] of weights) {
      for (const [b, w] of row) {
        if (a < b && w > pairW) { pair = [a, b]; pairW = w }
      }
    }
    if (!pair) {
      const bySize = [...clusters].sort((x, y) => x[1].members.size - y[1].members.size)
      pair = [bySize[0][0], bySize[1][0]]
    }
    // keep the larger as the survivor
    const [a, b] = pair
    const survivor = clusters.get(a).members.size >= clusters.get(b).members.size ? a : b
    const victim = survivor === a ? b : a
    merge(survivor, victim)
    mergedCap++
  }

  // --- 5: stable ids + finalize ----------------------------------------------
  const primaryAnchor = (c) => {
    // anchor with the greatest in-cluster weighted degree
    let best = null, bestW = -1
    for (const an of [...c.anchors].sort()) {
      let w = 0
      for (const [nbr, wt] of (adj.get(an) || new Map())) if (c.members.has(nbr)) w += wt
      if (w > bestW) { best = an; bestW = w }
    }
    return best ?? [...c.anchors].sort()[0] ?? [...c.members].sort()[0]
  }

  const oversizeLimit = Math.max(minSize * 5, Math.round([...clusters.values()].reduce((s, c) => s + c.members.size, 0) * 0.4))

  const out = []
  for (const c of clusters.values()) {
    const anchor = primaryAnchor(c)
    const members = [...c.members].sort()
    // which shared nodes does this cluster touch?
    const refs = new Set()
    for (const m of c.members) {
      for (const nbr of (adj.get(m)?.keys() || [])) if (shared.has(nbr)) refs.add(nbr)
    }
    out.push({
      id: 'feat_' + shortHash(anchor),
      anchor,
      anchors: [...c.anchors].sort(),
      members,
      size: members.length,
      sharedRefs: [...refs].sort(),
      oversized: members.length > oversizeLimit,
    })
  }
  out.sort((a, b) => b.size - a.size)

  const unclustered = movable.filter((id) => !label.get(id) && !shared.has(id)).sort()

  return {
    clusters: out,
    shared: [...shared].sort(),
    unclustered,
    summary: {
      featureCount: out.length,
      sharedCount: shared.size,
      unclusteredCount: unclustered.length,
      mergedTiny,
      mergedCap,
      oversized: out.filter((c) => c.oversized).map((c) => c.id),
      params: { sharedThreshold, maxFeatures, minSize },
    },
  }
}
