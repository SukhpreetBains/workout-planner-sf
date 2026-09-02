# Dependency-graph generator

Deterministic dependency graph + suggested feature clusters for a retrieved
Salesforce project. Replaces the LLM-driven feature inference in **Bootstrap
Step 3** of the `analyze-org` skill: the model goes from *inventing* the feature
tree to *naming and refining* a computed one.

## Install

```bash
cd plugins/ascent/skills/analyze-org/scripts
npm install        # one-time; pulls fast-xml-parser
```

## Run

From the Salesforce project root (after `sf project retrieve start` has populated
`force-app/`):

```bash
node plugins/ascent/skills/analyze-org/scripts/build-dependency-graph.mjs --org <alias>
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--org <alias>` | — | Org for the `MetadataComponentDependency` Tooling API query (backbone) |
| `--source <dir>` | `force-app` | Retrieved metadata root to parse |
| `--out <dir>` | `architecture/.dependency` | Where artifacts are written |
| `--shared-threshold <n>` | `3` | Float a node into *Shared* if it's referenced by ≥ n clusters |
| `--max-features <n>` | `15` | Cap suggested features; merge beyond this |
| `--min-size <n>` | `3` | Merge clusters smaller than this into their strongest neighbor |
| `--no-api` | off | Skip the Tooling API; parse-only |
| `--quiet` | off | Suppress progress logging |

## How it works

1. **Backbone (hybrid):** queries `MetadataComponentDependency` via the Tooling API
   for real, org-computed reference edges. If unavailable/empty, it degrades to
   parse-only and stamps `coverage: "reduced"` in the output.
2. **Gap-fill parsers (always run):** objects/fields/lookups/record types · Apex
   class→class and trigger→object/handler · Flow targets + LWC→FlexiPage · perm
   set / PSG access edges.
3. **Weighted graph:** edges are tiered strong/medium/weak (see `lib/weights.mjs`).
   Managed (`ns__`) components are kept as edge targets but never as cluster
   members.
4. **Object-anchored clustering:** seed one cluster per custom object/app, then
   propagate labels by edge weight. High fan-in utilities float into *Shared*.
   Guardrails merge sub-minimum clusters and cap the total; oversized clusters are
   flagged (not force-split).
5. **Stable output:** cluster ids are hashed from their anchor, so refreshes keep
   ids stable and carry over human/LLM-assigned `name` + `notes`; membership
   changes surface in a `drift` block.

## Artifacts (`architecture/.dependency/`)

- `graph.json` — nodes + typed/weighted edges + `coverage` flag. The
  LLM-consumable source of truth.
- `clusters.json` — suggested features (id, name, anchor, members, sharedRefs),
  plus `shared`, `unclustered`, `summary`, and `drift`.
- `graph.mmd` — a cluster-level Mermaid view for humans to eyeball. Clusters not
  yet named are marked with `*`.

## Tests

A synthetic fixture lives under `test/fixture/force-app` (three features sharing a
util class). Validate parse-only end-to-end:

```bash
node build-dependency-graph.mjs --no-api --source test/fixture/force-app --out /tmp/deps-test
```
