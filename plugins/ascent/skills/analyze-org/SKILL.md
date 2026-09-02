---
name: analyze-org
description: Map a Salesforce org's architecture into reusable per-feature reference files. On first run against an org, retrieves curated metadata via a bundled package.xml, works with the user to capture the org's shared domain vocabulary, and builds an architecture map written in those terms; on later runs, reads the existing map so agents orient quickly without re-scanning the org. Use when an agent needs a fast overview of what features/objects/automation exist in a target org.
---

# Analyze Org Skill

This skill maintains a **persistent architecture map** of a Salesforce org so any agent can understand the org's major features in seconds instead of re-scanning metadata every time.

The map lives at the **project root** in an [`architecture/`](../../../../architecture/) folder:

- `architecture/architecture.md` — the index: every major feature, one row each, linking to its detail file.
- `architecture/vocabulary.md` — the org's **shared domain language**: the team's word for each object/process, mapped to metadata. Built collaboratively with the user on first run; feature files are written in these terms.
- `architecture/features/<feature>.md` — one file per major feature (objects, automation, UI, access, entry points).

The map is generated from a target org but stored at the project level so any agent working in the project can read it.

---

## Decision: read the map, or build it?

Determine the **target org alias** (ask the user, or use the project default via `sf config get target-org`), then check whether a map already exists:

```bash
ls architecture/architecture.md
```

| State | Action |
|-------|--------|
| `architecture.md` **exists** | **Read the map** to find the relevant feature(s), then retrieve the current metadata for just those components and answer from it (see below). This is the common case. Don't re-scan the whole org — only the feature in play. |
| `architecture.md` **missing** | **Build it first.** Run the [Bootstrap procedure](references/bootstrap.md), then read the map. |
| User asks to **refresh** | Re-run the [Bootstrap procedure](references/bootstrap.md); it preserves hand-written notes. |

The skill's primary job is the first row: **orient against the existing references and relate them to what the user is asking about.** Bootstrap is a one-time (or on-demand) cost that produces the references you read.

---

## Using the map to answer a request

When a map exists, use the references to locate the right feature, then pull the **current** metadata for just that feature from the org before answering. The map orients you; the org is the source of truth for actual content.

1. **Start at the index, and learn the language.** Read `architecture/architecture.md`, then read `architecture/vocabulary.md` so you use the org's terms (and avoid their aliases) when you answer. The feature table tells you, at a glance, every major capability, its key objects, and which feature file describes it.

2. **Match the request to features.** Map what the user is asking about to one or more rows. The request usually names an object, a screen, a process, or a business capability — find the feature(s) that own it:
   - object/field question → the feature whose "key objects" list it
   - automation/behavior question → the feature whose triggers/flows target that object
   - UI/page question → the feature whose LWC/FlexiPage clusters build that page
   - "how does X relate to Y" → open both feature files and follow the cross-links

3. **Read the relevant feature files, not all of them.** Open only the `architecture/features/<feature>.md` files the request touches. Each one lists that feature's objects, automation, UI, access, and entry points (and links to related features — follow those when the request spans a boundary). Treat these lists as the **inventory of components to refresh** in the next step.

4. **Retrieve the latest metadata for those components.** The map can be stale — once you know which feature(s) are in play, pull the current version of their components straight from the org so you reason over what's actually deployed, not a snapshot. Build a targeted retrieve from the component names in the feature file(s):

   ```bash
   sf project retrieve start \
     --metadata "CustomObject:Obj__c" "ApexClass:NameHandler" "ApexTrigger:NameTrigger" \
                "Flow:Flow_Api_Name" "LightningComponentBundle:componentName" \
                "FlexiPage:FlexiPage_Name" "PermissionSet:PermSet_Name" \
     --target-org <org-alias>
   ```

   - Pull only the components named in the relevant feature file(s) — keep the retrieve scoped to the request, not the whole org.
   - Use `<type>:<name>` pairs (e.g. `ApexClass:AccountService`). For all members of a type use `<type>:*`, but prefer naming specific components.
   - If a component named in the map no longer retrieves, it's been renamed or deleted — note it, answer with what exists, and flag the map as stale.
   - Then read the freshly retrieved files under `force-app/` for the actual field definitions, Apex logic, flow steps, etc.

5. **Answer from the retrieved metadata.** Explain which features are involved, how they connect, and what the current components do — grounded in the files you just pulled, not just the map's summary. Cite the feature files for the map and the underlying components for the detail. Note any drift you saw between the map and the org.

If the map looks stale or incomplete for the request (missing a feature the user clearly has, or referencing components that no longer exist), tell the user and offer to refresh via the [Bootstrap procedure](references/bootstrap.md).

## References

- [`bootstrap.md`](references/bootstrap.md) — the first-run / refresh procedure that retrieves metadata and generates the map (read this only when building or refreshing).
- [`scripts/`](scripts/) — the **dependency-graph generator** (`build-dependency-graph.mjs`). Bootstrap Step 3 runs this to compute the candidate feature set deterministically instead of inferring it from raw metadata; it writes `architecture/.dependency/{graph,clusters}.json` + `graph.mmd`. See [`scripts/README.md`](scripts/README.md).
- [`references/LANGUAGE.md`](references/LANGUAGE.md) — how to build the shared vocabulary *with the user* on first run (read during Bootstrap Step 4).
- [`manifest/package.xml`](manifest/package.xml) — curated "important metadata" manifest used by Bootstrap (edit to change scope; this scope also feeds the dependency graph).
- [`references/README.md`](references/README.md) — how the auto-populated per-org folders work.
- [`references/_architecture-template.md`](references/_architecture-template.md) — template for the per-org index.
- [`references/_vocabulary-template.md`](references/_vocabulary-template.md) — template for the shared vocabulary.
- [`references/_feature-template.md`](references/_feature-template.md) — template for a single feature file.
