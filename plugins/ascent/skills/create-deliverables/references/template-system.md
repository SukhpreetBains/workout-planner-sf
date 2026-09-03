# Template system

Templates are user-facing compositions of reusable content-domain modules. The
implementation retains the internal `archetype` name for compatibility.

## Files

```text
templates/
  modules/<module-id>.json
  project-kickoff/
    archetype.json
    content.example.yaml
    intake.example.yaml
```

An archetype owns module order, question selection or promotion, and optional
output-mapping overrides. A module owns canonical question wording, stable IDs,
answer types, default tiers, and default output mappings.

## Module definition

Every module JSON file contains:

- `schema_version`: currently `1`
- `id`, `title`, and `description`
- `questions`: canonical question definitions
- `default_output`: the normal answer-to-component mapping

Every question contains:

- `id`: stable and prefixed with the module ID
- `tier`: `required` or `optional`
- `prompt`: concise user-facing wording
- `answer_type`: one of the types enforced by `scripts/lib/intake.mjs`
- `source_ref`: traceability back to the source question set

Template module entries may use `include_questions`, `exclude_questions`,
`promote_to_required`, and `output`. They do not rewrite canonical prompts.

## Intake states

Answers use one of these statuses:

- `answered`: contains a value matching the declared answer type
- `partial`: some evidence exists, but material parts are absent
- `conflicting`: available evidence disagrees
- `missing`: no supported answer exists
- `deferred`: the user chose not to answer yet
- `not_applicable`: the user explicitly marked it and supplied a reason

Only `answered` and `not_applicable` resolve a required question. Only a user
may set `not_applicable`.

An intake also records:

- `schema_version: 1`
- `template`
- `build_status`: `draft` or `final`
- `optional_review`: `pending`, `answer`, `skipped`, or `complete`
- `answers`: a mapping keyed by stable question ID
- `override.required_gaps_confirmed_at`: required for a final build with gaps

Every `answered` item records `answered_by` as `source`, `user`, or `mixed`,
plus a `disposition` of `rendered`, `summarized`, or `supporting`. Source-backed
answers include at least one source citation. This makes answer coverage a
machine-enforced gate instead of a drafting convention.

## Gap behavior

Required gaps do not disappear. A generated site contains:

- one opening summary grouped by module
- the unanswered question inside the section it would have populated
- a generated manifest list of unresolved IDs

Optional gaps are warned about before building and retained in intake, but are
not rendered.

The user may explicitly override required gaps and may mark the result final.
The system records the confirmation and keeps the gap indicators. It never
invents substitute content.

## Human review

The machine-readable content file remains the source, but the branded draft is
the review surface. Do not ask a user to approve raw YAML. After the first
render, offer customizations. A confirmed customization request detaches the
site into local editable source and stops enforcing module and template shape.
