---
name: compose-deliverable
description: Build an editable Slalom-branded PowerPoint deck from the same approved content.yaml used for a microsite. Use when a discovery readout, findings summary, roadmap, or business case must be delivered as a native .pptx rather than a web experience.
---

# Compose deliverable

Turn approved engagement content into a native, editable PowerPoint deck. This
skill renders findings; it does not invent findings, sources, or numbers.

## Quick start

```bash
cd plugins/ascent/skills/compose-deliverable
npm install
npm test
npm run demo

# Build approved content using the shared create-deliverables contract.
node scripts/build.mjs ../create-deliverables/templates/executive-readout/content.example.yaml \
  --out build/executive-readout.pptx
python3 scripts/validate_pptx.py build/executive-readout.pptx \
  --manifest build/executive-readout.manifest.json
```

The build also writes an HTML conversion preview beside the deck. It is an
intermediate fixed 16:9 slide stage, not a microsite and not a handoff artifact.

## Workflow

1. Locate the approved source artifact. Never author findings in this skill.
2. Draft and approve `content.yaml` using `create-deliverables`' content contract.
3. Confirm the deck title, classification, accent, and slide sequence. Use a
   reviewed storyboard JSON when a dense section must split across slides.
4. Build the `.pptx`; the browser dependency is isolated in this skill.
5. Run structural validation and inspect the deck in PowerPoint before handoff.
6. Invoke the brand mode of `utilities-ui-generation` for the final visual and accessibility review.

## Current scope

This is a reference-informed implementation for the `executive-readout`
archetype. It preserves text as editable PowerPoint text, uses native shapes for
layout, supports trusted local partner logos, and emits a fixture-derived
manifest for structural validation. An explicit storyboard can split findings,
recommendations, and other collection sections without losing or repeating
source items.

The authenticated Project Airhead example confirmed that structured source
content exists beside the generated microsite. Customer content is not retained
in Git; the default demo uses the synthetic reconstruction and storyboard in
`examples/`. See `references/reference-informed-storyboard.md` for the bounded
inventory and proposed section-to-slide mapping.

## Non-negotiables

- Read from the shared content contract; do not scrape the microsite DOM.
- Every number is measured and sourced or explicitly marked absent.
- Avenir Next LT Pro is the PowerPoint face. Never embed Slalom Sans in a deck.
- Read colors from `assets/powerpoint-tokens.json`; do not add color literals to
  renderer code or generated content.
- Use only approved Slalom artwork from the sibling `utilities-ui-generation` skill's active branding pack.
- Do not commit client artifacts. Fixtures must be synthetic or approved and
  redacted.
- A successful export is not sufficient: validation must find native text in
  the PPTX package so a raster-only deck cannot pass.
- A storyboard must cover every source section item exactly once and preserve
  source order.
- The fixed-stage preview must make no external requests and must pass overflow
  validation before PowerPoint export begins.

## Dependencies

`dom-to-pptx` 2.1.1 is pinned locally and brings Puppeteer/Chromium. This
deliberately does not change `create-deliverables`' zero-dependency contract.
The fixed 1920x1080 conversion stage follows the useful layout discipline from
`frontend-slides`; its screenshot-to-PDF export is not used because it does not
produce editable PowerPoint content.

See `references/architecture.md` for the decision record and `DEMO.md` for the
Monday demonstration sequence and known limits.
