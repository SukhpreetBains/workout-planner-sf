#!/usr/bin/env node
// analyze-org dependency-graph generator.
//
// Builds a deterministic dependency graph + suggested feature clusters from a
// retrieved Salesforce project, replacing the LLM-driven feature inference in
// Bootstrap Step 3. Hybrid sourcing: MetadataComponentDependency (Tooling API)
// backbone + offline XML/Apex parsing gap-fill; degrades to parse-only with a
// reduced-coverage flag if the API is unavailable.
//
// Usage:
//   node build-dependency-graph.mjs --org <alias> [--source force-app] \
//        [--out architecture/.dependency] [--shared-threshold 3] \
//        [--max-features 15] [--min-size 3] [--no-api] [--quiet]

import { Graph } from './lib/graph.mjs'
import { fetchApiDependencies, applyApiEdges } from './lib/edges-api.mjs'
import { parseLocalMetadata } from './lib/parsers.mjs'
import { cluster } from './lib/cluster.mjs'
import { writeArtifacts } from './lib/output.mjs'
import { makeLogger } from './lib/util.mjs'

function parseArgs(argv) {
  const o = {
    org: null,
    source: 'force-app',
    out: 'architecture/.dependency',
    sharedThreshold: 3,
    maxFeatures: 15,
    minSize: 3,
    noApi: false,
    quiet: false,
  }
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i]
    const next = () => argv[++i]
    switch (a) {
      case '--org': o.org = next(); break
      case '--source': o.source = next(); break
      case '--out': o.out = next(); break
      case '--shared-threshold': o.sharedThreshold = Number(next()); break
      case '--max-features': o.maxFeatures = Number(next()); break
      case '--min-size': o.minSize = Number(next()); break
      case '--no-api': o.noApi = true; break
      case '--quiet': o.quiet = true; break
      case '-h': case '--help': o.help = true; break
      default: console.error(`Unknown argument: ${a}`); o.help = true
    }
  }
  return o
}

const HELP = `analyze-org dependency-graph generator

  --org <alias>            Target org for MetadataComponentDependency (Tooling API)
  --source <dir>           Retrieved metadata root (default: force-app)
  --out <dir>              Output dir (default: architecture/.dependency)
  --shared-threshold <n>   Float a node into Shared if it touches >= n clusters (default: 3)
  --max-features <n>       Cap suggested features; merge beyond this (default: 15)
  --min-size <n>           Merge clusters smaller than this (default: 3)
  --no-api                 Skip the Tooling API; parse-only
  --quiet                  Suppress progress logging
`

function main() {
  const opts = parseArgs(process.argv)
  const log = makeLogger(opts.quiet)
  if (opts.help) { console.log(HELP); process.exit(0) }

  const graph = new Graph()

  // 1. Backbone — MetadataComponentDependency (unless --no-api).
  let coverage = 'reduced'
  if (!opts.noApi) {
    const api = fetchApiDependencies(opts.org, log)
    if (api) { applyApiEdges(graph, api.records, log); coverage = 'full' }
  } else {
    log.info('--no-api set; parse-only mode.')
  }

  // 2. Gap-fill — offline parsers (always run).
  parseLocalMetadata(graph, opts.source, log)

  const stats = graph.stats()
  log.info(`Graph: ${stats.nodes} nodes (${stats.externalNodes} external), ${stats.edges} edges, ${stats.anchors} anchors.`)
  if (!stats.anchors) {
    log.error(`No anchor objects found under "${opts.source}". Is this a retrieved Salesforce project? Nothing to cluster.`)
    process.exit(2)
  }

  // 3. Cluster.
  const clustering = cluster(graph, {
    sharedThreshold: opts.sharedThreshold,
    maxFeatures: opts.maxFeatures,
    minSize: opts.minSize,
  })

  // 4. Emit.
  const meta = {
    generatedAt: new Date().toISOString(),
    coverage,
    source: opts.source,
    org: opts.org,
  }
  writeArtifacts(opts.out, graph, clustering, meta)

  const s = clustering.summary
  log.info(`Wrote ${opts.out}/graph.json, clusters.json, graph.mmd`)
  console.error(
    `\n[deps] ${s.featureCount} feature(s), ${s.sharedCount} shared, ${s.unclusteredCount} unclustered ` +
    `(coverage: ${coverage}; merged ${s.mergedTiny} tiny + ${s.mergedCap} to cap` +
    `${s.oversized.length ? `; oversized: ${s.oversized.join(', ')}` : ''}).`,
  )
}

main()
