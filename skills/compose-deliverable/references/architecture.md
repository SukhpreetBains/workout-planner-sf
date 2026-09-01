# Architecture decision

Status: reference-informed implementation candidate for the Monday demo on 2026-08-28.

## Decision

Render PowerPoint from the shared `content.yaml`, not from a completed
microsite. The content contract is the stable source of truth; web and deck are
separate renderers over it. The deck renderer assigns explicit slide boundaries
instead of guessing where a continuous page should break.

Use `dom-to-pptx` inside `compose-deliverable` only. Its Puppeteer dependency is
deliberately isolated so `create-deliverables` remains a zero-dependency build.
The intermediate HTML is a conversion substrate, not a customer artifact.

## External repository assessment

`zarazhangrui/frontend-slides` is inspiration, not the engine. Its fixed
1920x1080 stage, visual approval previews, and progressive template disclosure
are useful patterns. Its conversion flow goes from PowerPoint to HTML, and its
exporter screenshots slides into PDF. It has no HTML-to-PPTX path and cannot
produce editable native PowerPoint elements.

This spike adopts the fixed-stage discipline. `dom-to-pptx` then maps computed
DOM geometry to PptxGenJS text boxes and shapes. Structural validation inspects
the OOXML package and rejects slides without native text or shapes.

## Approved constraints

- Skill name: `compose-deliverable`.
- Branch: continue `feature/dom-to-pptx-skill`; story number remains TBD.
- Dependency: Puppeteer is allowed only inside this skill.
- Eval: build after `feature/skill-evals` reaches `main`; do not duplicate it.
- Golden reference: request Gada's approved deck; use synthetic content until
  it is available and cleared for the repository.

## Reference inspection update

Authenticated SharePoint inventory on August 28 confirmed that the example has
`content.json` beside the generated `site/` folder. The published folder contains
`index.html`, `bundle.html`, `brand-manifest.json`, local CSS, local Slalom Sans
webfonts, local JavaScript, and an approved Slalom wordmark. This classifies the
input route as shared structured content; no DOM importer is needed for the
Monday cut.

The connector could list but not extract the JSON file. The rendered HTML was
used only to confirm ordered section types and density. Customer copy, metrics,
logos, and files are not stored in this repository. The committed demo is a
labelled synthetic reconstruction.

## Known limits

- The demo proves reference-informed section coverage, native editability, and
  structural gates, not final customer-template fidelity or evaluation quality.
- The generated PPTX names `Avenir Next LT Pro`. macOS Quick Look cannot access
  Microsoft Office's private cloud-font cache and may substitute a serif face;
  inspect the final file in PowerPoint for delivery review.
- `npm audit` reports high-severity denial-of-service advisories in
  `image-size`, inherited through PptxGenJS, with no published fix for this
  dependency chain. The demo accepts only trusted local assets. Arbitrary image
  uploads are out of scope until the dependency is patched or replaced.
