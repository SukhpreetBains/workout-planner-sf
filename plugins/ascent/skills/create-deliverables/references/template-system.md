# Template system

Templates are user-facing compositions of reusable content-domain modules. The
implementation retains the internal `archetype` name for compatibility.

## Files

```text
templates/
  project-kickoff/
    archetype.json
    content.example.yaml
    intake.example.yaml
modules/
  shared/
    primitives.mjs
  <module-id>/
    module.json
    html.mjs
    example.json
```

An archetype owns module order, question selection or promotion, and optional
output-mapping overrides. A module owns canonical question wording, stable IDs,
answer types, default tiers, explicit output mappings, and the HTML for every
module view. Each module's `html.mjs` lives beside its `module.json`. Shared
escaping, prose, data-table, meter, and brand primitives live in
`modules/shared/primitives.mjs`; shared code does not own finished module views.

## Module definition

Every module JSON file contains:

- `schema_version`: currently `1`
- `id`, `title`, and `description`
- `questions`: canonical question definitions
- `default_output`: the normal answer-to-view mapping

Every output mapping contains:

- `id`: the module-local view ID used by authored content
- `type`: the section schema used to validate the view's data
- `renderer`: a relative `.mjs` path and named renderer, such as
  `./html.mjs#agenda`
- `uses`: the question IDs that normally supply the view

Every renderer path must reference the `html.mjs` in the same module folder.
Module renderers may import low-level primitives from `modules/shared/`, but
one module never imports a finished view from another module.

## Module examples

Every module owns `example.json`, a fictional, renderable demonstration of all
authorable views declared by that module. A module that owns the template cover
also supplies the fictional cover metadata. Example source never contains real
client information and is validated against the same content schemas and HTML
renderers used for deliverables.

Render one module directly:

```bash
node scripts/build.mjs --preview-module kickoff-context \
  --out path/to/module-preview \
  --bundle
```

Render every module selected by a template:

```bash
node scripts/build.mjs --preview-template project-kickoff \
  --out path/to/template-preview \
  --bundle
```

Template previews compose the module-owned examples in template order and add a
visible module label to every section. Show this preview when a user selects a
template, then explain that they may choose which modules to include in their
output before intake begins.

Every question contains:

- `id`: stable and prefixed with the module ID
- `tier`: `required` or `optional`
- `prompt`: concise user-facing wording
- `answer_type`: one of the types enforced by `scripts/lib/intake.mjs`
- `source_ref`: traceability back to the source question set

Template module entries may use `include_questions`, `exclude_questions`,
`promote_to_required`, and `output`. They do not rewrite canonical prompts.

Initial guided content identifies every authored section with `module` and
`view`. The build derives the section type and renderer from `module.json`.
Authored `type` values are rejected in guided mode so the content cannot drift
from its module contract. After detachment, the generated HTML can be changed
without conforming to modules or templates.

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

For live workspace intake, source-backed values come from current reviewed
tracker rows in `workspace/.system/tracker-copies/`, not the source documents.
Refresh them once with `shared/scripts/sync.py --trackers-only`, using the
installed plugin's Python wrapper and the Opportunity's `EAD_REPO_ROOT`.
In each answer's `sources` list, use `source_id` for the tracker-copy path and
`locator` for the stable row ID and field names. Preserve the row's original
source references for provenance without reopening the documents. Explicit
user answers remain `answered_by: user`; a missing reviewed value remains a
gap until review acceptance or a direct user answer resolves it.

## Gap behavior

Required gaps remain recorded in the intake and generated manifest. A draft
shows one compact notice above the cover with the unanswered required-question
count. It does not inject missing questions, gap-only sections, or placeholders
into the page. Author only supported fields, rows, and views; omit a view when
there is not enough supported content to satisfy its schema. Keep the supported
parts of partially answered modules.

An explicit draft request does not require a gap interview or separate
incomplete-build confirmation before rendering. Show the draft first and offer
gap resolution afterward. An explicitly confirmed final build retains the
opening summary grouped by module and contextual unanswered questions.

Optional gaps are warned about before building and retained in intake, but are
not rendered.

The user may explicitly override required gaps and may mark the result final.
The system records the confirmation and keeps the final gap indicators. It never
invents substitute content.

## Human review

The machine-readable content file remains the source, but the branded draft is
the review surface. Do not ask a user to approve raw YAML. After the first
render, offer customizations. A confirmed customization request detaches the
site into local editable source and stops enforcing module and template shape.

## Custom template instructions and visual preferences

An optional `instructions` field in `archetype.json` names a Markdown file inside
the template directory. The loader validates and reads it as `instructionsText`;
the guided workflow reads it on selection and resume. Templates without the field
retain their existing behavior. Missing files, empty instructions, and paths
outside the template (including symlinks) fail validation.

Optional `template_questions` hold presentation preferences, separate from module
content questions. Each has a template-prefixed `id`, `prompt`, `tier`,
`answer_type: decision`, and at least two `choices`. Each choice has a unique
`value`, `label`, and local `image` path. A `brand:` prefix resolves inside the active branding pack’s
assets directory, avoiding duplicate assets across templates. Answer them through the normal intake
with explicit user provenance. Required gaps, not-applicable reasons, draft
builds, and final overrides use the same rules as module questions.

`cover_background_question` references one of these questions. An answered choice
provides the cover image; unresolved or explicitly not-applicable answers leave
the existing solid cover. The builder writes `template-choices.html` with every
choice shown, and copies the assets locally for offline use. No background is
automatically chosen for structure previews.

Optional `illustrations` entries target a selected `module` and `view`, using a
local `image` as a decorative section-heading accent. Only authored sections
render their accents. Keep approved asset provenance in the template assets
README. The HLS kickoff template demonstrates all of these fields.
