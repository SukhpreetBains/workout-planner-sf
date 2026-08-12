# Bootstrap — building the architecture map (first run / refresh only)

Run this procedure **only** when no map exists for the project, or when the user explicitly asks to refresh. On every other invocation, read the existing map instead (see [`README.md`](README.md) and the skill's reading path).

The output lives at the **project root** under `architecture/`:

- `architecture/architecture.md` — the index.
- `architecture/vocabulary.md` — the org's shared domain language (built with the user).
- `architecture/features/<feature>.md` — one file per major feature.

---

## Step 1 — Confirm before retrieving

Retrieving metadata writes files into the project and can be slow on large orgs. Tell the user what will happen and confirm:

> "No architecture map exists for this project yet. I'll retrieve curated metadata (objects, fields, Apex, triggers, flows, LWC, FlexiPages, tabs, apps, permission sets) from **<org-alias>** into `force-app/`, then build a feature map under `architecture/` at the project root. Proceed?"

## Step 2 — Retrieve metadata

The curated manifest lives at [`../manifest/package.xml`](../manifest/package.xml). Retrieve into the current Salesforce project's `force-app/` (standard sfdx layout):

```bash
sf project retrieve start \
  --manifest .agent-framework/skills/analyze-org/manifest/package.xml \
  --target-org <org-alias>
```

- If the command reports it's not in an sfdx project, `cd` to the Salesforce project root first (the dir with `sfdx-project.json`).
- If retrieve fails for specific components, note them, remove offending entries from a local copy of the manifest, and re-run. Record anything that couldn't be retrieved.
- To widen/narrow scope, edit `manifest/package.xml` (see comments inside it).

## Step 3 — Compute the dependency graph and candidate features (script)

**Do not infer features by reading raw metadata.** Run the bundled generator
([`../scripts/`](../scripts/)); it computes a deterministic dependency graph and
proposes feature clusters for you. Your job in later steps is to **name and
refine** those clusters, not invent them.

First-time only, install the one dependency:

```bash
cd .agent-framework/skills/analyze-org/scripts && npm install && cd -
```

Then, from the Salesforce project root (where `force-app/` was populated in Step 2):

```bash
node .agent-framework/skills/analyze-org/scripts/build-dependency-graph.mjs \
  --org <org-alias>
```

This writes three artifacts to `architecture/.dependency/`:

- `clusters.json` — **the candidate feature set**: each cluster has a stable `id`,
  an `anchor` object, its `members`, and `sharedRefs`. This is your starting point.
- `graph.json` — the full node/edge graph (consult when a cluster looks wrong or a
  relationship is unclear).
- `graph.mmd` — a cluster-level Mermaid view to eyeball.

How it derives features (so you can trust/critique it): a hybrid of the org's
`MetadataComponentDependency` Tooling API (backbone) plus offline parsing of the
retrieved tree (objects/fields/lookups/record types, Apex refs, Flow/LWC/FlexiPage
wiring, perm-set grants). Edges are weighted; clusters are anchored on custom
objects/apps; high fan-in utilities float into a **Shared** group; managed
(`ns__`) components are kept as edges but never as cluster members.

**Read `clusters.json` and reconcile it:**

- Check `coverage`. If it's `"reduced"`, the Tooling API was unavailable and the
  graph came from parsing alone — expect some missing edges and lean more on your
  own reading where a cluster looks thin.
- Each cluster with `"named": false` still needs a business name — you'll assign it
  in Step 5/6. The `name` field holds a placeholder derived from the anchor object.
- Use the cluster `members` as the **inventory** for each feature file. Treat
  `shared` and `unclustered` lists as cross-cutting utilities and orphans
  respectively.
- You may merge/split clusters when the business reality differs from the graph —
  but start from what the script produced. The `summary` reports how many clusters
  were auto-merged and flags any `oversized` ones worth splitting.

The script targets **3–15 features** automatically (merging tiny clusters, capping
the total). If the result still seems off, re-run with `--max-features`,
`--min-size`, or `--shared-threshold` (see [`../scripts/README.md`](../scripts/README.md)).

## Step 4 — Build the shared vocabulary *with the user* (first run)

Before writing any feature files, establish the org's **domain language** so every file is written in the team's words. Follow the facilitation guide in [`LANGUAGE.md`](LANGUAGE.md):

- From the metadata and the features you just identified, draft 8–20 candidate terms (object→business name, named processes, naming-prefix meanings, key personas/statuses) with a guessed definition and metadata mapping.
- Present them to the user and ask targeted questions where the metadata is ambiguous. Let them rename, merge, drop, and add terms — **they own the words**.
- Write the confirmed list to `architecture/vocabulary.md` (project root, next to `architecture.md`) from [`_vocabulary-template.md`](_vocabulary-template.md).

**On refresh:** the vocabulary is hand-curated — do **not** regenerate it. Read the existing `architecture/vocabulary.md`, propose only additions for new metadata, confirm with the user, and preserve every existing term.

## Step 5 — Write the feature files

For each feature, create `architecture/features/<feature-slug>.md` (at the project root) from the template in [`_feature-template.md`](_feature-template.md). Keep each file tight — it's a map, not full documentation. **Use the vocabulary terms from Step 4 exactly** (the team's word for each object/process, not the raw API name), and link related features with relative links (sibling files in `features/`).

## Step 6 — Write / refresh the architecture index

Create `architecture/architecture.md` (at the project root) from [`_architecture-template.md`](_architecture-template.md):

- A link to `vocabulary.md` near the top, so readers learn the language before the features.
- A feature table: name → one-line purpose → key objects → link to the feature file (e.g. `features/<feature-slug>.md`).
- Org-wide notes: API version, retrieve date, manifest used, anything that couldn't be retrieved.
- A cross-cutting section (shared utilities, integration points, permission model).

**On refresh:** regenerate the generated sections but preserve any content under a `## Notes` / `<!-- manual -->` block a human added. Update the "Last analyzed" date.

## Step 7 — Report

Tell the user how many features were mapped, how many vocabulary terms were agreed, and where the files live. Point future agents at `architecture/architecture.md` as the entry point.
