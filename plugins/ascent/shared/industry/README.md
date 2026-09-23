# Industry packs

An industry pack is optional reference content — vocabulary, extraction
emphasis, review considerations, and deliverable framing — that the
agnostic Ascent skills (`workspace-add`,
`workspace-review`, `create-deliverables`) may layer on top of
their normal behavior when one is active for an Opportunity. It never
changes what those skills fundamentally do, and it never touches
`shared/schema/trackers.yaml`: every industry shares the same tracker
categories, columns, and engine. A pack only shapes how a skill
interprets and frames content within that unchanged schema.

No industry pack is the default and fully-supported state, not a
fallback. A workspace with no industry set, or explicitly set to `none`,
behaves exactly as if this folder did not exist.

## Contract

Each pack lives at `shared/industry/<id>/` with this shape:

```text
shared/industry/<id>/
  manifest.json
  references/
    overview.md               # domain primer: who the client is, common
                               # workstreams, stakeholder archetypes,
                               # regulatory/market landscape
    vocabulary.md              # standard terms and acronyms, so extraction
                               # and deliverables use client-familiar language
    ingestion-guidance.md      # what workspace-add should weight
                               # or watch for when classifying and extracting
                               # from this industry's source material
    review-guidance.md         # what workspace-review should double
                               # check before a person approves a proposed row
    deliverable-guidance.md    # terminology, tone, and section emphasis for
                               # create-deliverables output
  examples/
    fictional-client.md        # one consistent fictional client for this
                                # industry, reused across every worked example
                                # so they don't contradict each other
    <template>-static-example.json  # optional: a full alternate static
                                # example for one create-deliverables
                                # template, flavored for this industry.
                                # Same completeness bar as that template's
                                # own static example — every selected
                                # module's non-cover view, no more, no
                                # fewer. Rendered with:
                                #   node scripts/build.mjs \
                                #     --preview-template <template> \
                                #     --industry <id> --bundle
  assets/
    illustrations/             # optional: industry-appropriate imagery, only
    iconography/                # where the base library doesn't already cover it
```

`manifest.json`:

```json
{
  "schema_version": 1,
  "id": "<id>",
  "title": "<Human-readable name>",
  "description": "<One sentence, used when a skill lists available packs>",
  "references": {
    "overview": "references/overview.md",
    "vocabulary": "references/vocabulary.md",
    "ingestion_guidance": "references/ingestion-guidance.md",
    "review_guidance": "references/review-guidance.md",
    "deliverable_guidance": "references/deliverable-guidance.md"
  },
  "examples": {
    "fictional_client": "examples/fictional-client.md",
    "static_examples": {
      "<template-name>": "examples/<template-name>-static-example.json"
    }
  }
}
```

`static_examples` is optional and keyed by `create-deliverables` template
name; a pack need not cover every template. An entry is a **full
alternate** static example, not a partial patch layered onto the
template's own file — it's validated exactly the same way (every
selected module's non-cover view exactly once), so it has to stand
entirely on its own.

## How a pack gets activated

`workspace/.system/project.yaml` may carry an `industry:` key: an id
matching a `shared/industry/<id>/` folder, or the literal `none`.

- **Absent entirely** — this Opportunity has never been asked. The first
  skill that checks (`initial-setup` during setup, or whichever of the
  three consulting skills runs first otherwise) asks once, offers every
  pack found under this folder plus a "none of these" option, and writes
  whichever the user picks. This is a short, closed, confirmatory
  question — the same shape as `initial-setup`'s existing storage and
  messaging questions — never a request to compose engagement detail.
- **`none`** — asked and declined. Never asked again. Every skill runs
  exactly as documented, no different from a pack never having existed.
- **`<id>`** — that pack's `references/` are read alongside the skill's
  normal instructions, as emphasis and framing, never as a replacement for
  them.

An explicit in-conversation instruction ("use HLS for this",
"don't apply industry flavor here") always overrides the stored value for
that turn, without changing what's persisted unless the user says so.

## Adding a new industry pack

1. Create `shared/industry/<id>/` with the shape above. Write real,
   genuinely useful starter content for each reference file — not empty
   stubs.
2. Never add or imply a change to `shared/schema/trackers.yaml`. If a
   pack's guidance can't be expressed within the existing tracker
   categories and columns, that's a sign the guidance belongs in a
   reference file's prose (as interpretation or emphasis), not as new
   structure.
3. Reuse an existing fictional client across a pack's own examples if one
   already exists elsewhere for that industry, rather than inventing a
   second, inconsistent one.
4. No code change is required for a new pack to be discoverable — every
   consuming skill scans this folder for `manifest.json` files rather
   than naming packs by id.
