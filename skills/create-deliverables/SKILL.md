---
name: create-deliverables
description: "Build a Slalom-branded client deliverable as a microsite — an interactive static web page for discovery readouts, findings summaries, roadmaps, and business cases. Use when a deliverable should be a web experience rather than a deck or document. Composes Slalom brand tokens and Anime.js motion, and validates brand and accessibility compliance before handoff."
---

# Create deliverables — Slalom-branded microsites

Turns approved engagement content into a self-contained, brand-compliant
microsite. **This skill is a presentation layer.** It renders findings that a
specialist skill or the consultant already produced; it does not author findings,
invent numbers, or decide recommendations.

This skill owns the web medium only.

## Quick start

```bash
# 1. Draft content from an approved artefact, then show it to the user.
cp templates/executive-readout/content.example.yaml ./content.yaml

# 2. Build. The brand gate runs automatically as the final step.
node scripts/build.mjs ./content.yaml --out ./build/client-readout

# 3. Look at it. Motion needs a server; ES modules do not load over file://.
cd build/client-readout && python3 -m http.server 8000

# One self-contained file for email, which also opens straight off disk:
node scripts/build.mjs ./content.yaml --out ./build/client-readout --bundle
```

Run `node scripts/test/run.mjs` after changing anything under `scripts/` or
`assets/`.

## The workflow, in one line each

1. **Locate the content** — ask which approved artefact this renders.
2. **Choose the archetype** and confirm the shape fits the material.
3. **Draft `content.yaml`** and get the user's confirmation. This is the
   editorial checkpoint, and it is far cheaper than correcting built output.
4. **Confirm the accent** (one secondary colour) **and the motion level**.
5. **Build, then read the gate result** — honestly, warnings included.
6. **Hand off** per `references/delivery.md`.

Full detail in `references/workflow.md`.

## Where to look

| Task | Reference |
|---|---|
| Running the whole job end to end | `references/workflow.md` |
| Writing or debugging `content.yaml` | `references/content-contract.md` |
| What each component does, and adding one | `references/component-kit.md` |
| Choosing or adding an archetype | `references/archetypes.md` |
| Motion vocabulary, restraint rules, recipes | `references/motion-doctrine.md` |
| Grid, type scale, spacing, print | `references/layout-system.md` |
| Handoff, confidentiality, font licensing | `references/delivery.md` |
| A brand judgement call this skill does not cover | invoke `utilities-ui-generation` (brand) |
| A motion request outside the documented vocabulary | invoke `utilities-ui-generation` (motion) |

## Content-contract first

The microsite is a pure function of one `content.yaml` (or `.json`). Nobody
hand-edits output HTML — the build wipes and rewrites the output directory, so a
manual edit is silently lost, which is the safest failure mode available. If a
change cannot be expressed in the content contract, extend a component or add an
archetype and rebuild.

## Non-negotiables

- **Content comes from approved engagement artefacts. This skill renders; it
  does not author findings or invent numbers.** An empty section is a question
  for the consultant, not a gap to paper over.
- **Never hand-edit built output.** Change the content and rebuild.
- **Never hardcode a colour.** `tokens.css` is the only file in a deliverable
  allowed to hold a literal, and the validator errors on any hex, `rgb()`, or
  `hsl()` found elsewhere.
- **The validator gate must pass before anything reaches a client.**
  `--no-validate` is for mid-edit iteration only.
- **Never ship a deliverable that makes an external request.** No CDN, no font
  service, no analytics, no tracking pixel. Zero network requests at runtime.
- **Slalom Sans is the web face. Avenir Next LT Pro is PowerPoint-only** and must
  never appear in web output.
- **A Slalom Blue in every composition, and at most one secondary colour.** The
  accent is enforced structurally: components reference `var(--accent)` and never
  a named secondary.
- **Nothing conveys meaning by colour alone**, and nothing conveys meaning by
  motion alone. Severity is a meter *plus* a word; a heatmap cell prints its
  numeral.
- **Never invent a logo, icon, or illustration.** Take them from
  the active branding pack's `assets/`.
- **Resolve the Slalom Sans licensing question before the first handoff.**
  See `references/delivery.md`.

## Layout

```
scripts/
  build.mjs             content -> static site folder, then the gate
  validate-brand.mjs    the delivery gate; also runnable on its own
  lib/                  yaml · content · components · assets · bundle · report
  test/run.mjs          the whole suite, zero dependencies
assets/
  css/                  tokens · base · components · print
  js/motion.js          the motion vocabulary over Anime.js v4
templates/
  executive-readout/    archetype.json + a complete worked example
references/             one file per topic, listed above
```

## Assets and dependencies

Zero npm dependencies and zero runtime dependencies. Node's standard library
only. A sibling skill, `utilities-ui-generation`, supplies the raw material,
resolved by relative path:

- The active branding pack's `assets/` (resolved via
  `../utilities-ui-generation/branding/active.json`) — webfonts, the four
  approved logo colours, approved icons, illustrations, colour bars. Slalom's
  own pack ships as the default.
- `../utilities-ui-generation/assets/animejs/vendor/` — a pinned Anime.js
  v4.5.0 ESM bundle (MIT) and its licence, which is copied next to the bundle
  on every build.

The dependency on those **assets** is hard: the build fails with an actionable
message rather than emitting a deliverable with a missing logo or font.
Everything is copied into the output, never symlinked, so the result is
self-contained.

## Verify

`node scripts/test/run.mjs` covers the YAML subset parser (including every
construct it refuses), content validation, an end-to-end build, `--bundle`, and
every validator rule against a deliberately broken build — a validator that has
never failed is not known to work.

Then check what a machine cannot: scroll it, reload it with reduced motion on,
print it, load it with JavaScript disabled, and tab through it. The checklist is
at the end of `references/delivery.md`.
