# Kickoff citation UI study

The shared `create-deliverables` builder now uses one Sources disclosure per cited module. Use `node docs/mockups/kickoff-source-panels/implementation-preview.mjs` for the current implementation, the [citation contract](../../../plugins/ascent/skills/create-deliverables/references/citations.md) for authoring, and the [real-scenario checklist](real-scenario-checklist.md) when source material is available. The original two-mode study below remains a comparison artifact.

Current implementation captures: [desktop floating panel](../../screenshots/citations-ui/implementation-desktop.png) and [390px mobile disclosure](../../screenshots/citations-ui/implementation-mobile.png). Both use fictional source text and reduced motion.

[Open the standalone timeline HTML example](example-timeline.html) after downloading or checking out the PR, then scroll to the timeline and open Sources. It is generated from the shared builder with fictional citations. This review copy omits embedded Slalom Sans font data and uses the browser's fallback font. Regenerate it with `node docs/mockups/kickoff-source-panels/implementation-preview.mjs --update-example`.

Two local prototypes layered onto the current Ascent project-kickoff renderer:

- **Floating notes:** section-specific disclosures anchored to the right, opening over the content without resizing it.
- **Margin notes:** the same disclosures expand a right column, retaining the content alongside the evidence.

The current implementation has one control per module, collapsed initially, listing the displayed value, original document, source locator, exact excerpt, and accepted review record for each citation. Mobile places the disclosure below its module. Escape returns focus to the control. The original comparison prototypes below used individual tabs and DOM highlighting; those are no longer part of the shared builder.

The deck uses the actual template examples, module renderers, self-hosted Slalom Sans, wordmarks, and styles from main. Source documents and approval records are **fictional fixtures**. The examples also show direct user input, a changed date requiring review, and absent provenance. This study data does not represent production approval or evidence.

## Build and review

From the repository root:

```sh
node docs/mockups/kickoff-source-panels/build.mjs
python3 -m http.server 8766 --bind 127.0.0.1 --directory build/kickoff-source-panels/editable/dist
```

Open the following in VS Code's integrated browser:

- `http://127.0.0.1:8766/?mode=floating#s2-timeline-roadmap`
- `http://127.0.0.1:8766/?mode=margin#s2-timeline-roadmap`

The builder generates a baseline using Ascent's build function, detaches it, applies the study's local additions, and runs the detached rebuild and brand gate. `build/kickoff-source-panels/` is generated and owned by this builder; rebuilding replaces its `editable/` subtree. Edit the files beside this README to preserve changes across builds. Shared plugin sources are unchanged.

Source links open bundled, numbered source fixtures at the cited line. Review-trail links open the matching sample review record. This study stays local; it does not publish or redistribute font files to clients.

## Validation and limits

The current main template baseline and this mockup both produce 350 brand-gate errors, primarily in the inherited reference-layout stylesheet; the citation additions introduce zero additional errors. The builder saves the full comparison in `build/kickoff-source-panels/validation.json` and retains a nonzero exit code when the full gate fails. This is a local UI study, not a client-ready deliverable. Existing warnings cover centered workflow titles, typography density, and Slalom Sans redistribution.

Static checks verified JavaScript syntax, unique HTML IDs, every local resource and source-passage anchor, all 12 initially collapsed disclosures, and all sample quotes against their saved source lines.

Local Chromium review covered floating and margin layouts at 1600px, the timeline's expanded phase alongside an open citation, passage-link navigation, phase highlighting, Enter to open, Escape to close and restore focus, one open citation per module, and the global Sources toggle. The 390px mobile view has no horizontal overflow. No browser JavaScript errors occurred. Captures used reduced motion; print and no-JavaScript treatments remain unverified. The integrated browser connection was unavailable, so these checks used a separate headless browser.

Screenshots are saved in [`docs/screenshots/citations-ui`](../../screenshots/citations-ui/) for PR discussion. All depicted quotes and approval records are illustrative.
