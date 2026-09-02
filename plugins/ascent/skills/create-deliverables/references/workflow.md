# Workflow

Discover → propose → build → validate → hand off. The consultant keeps editorial
control at every step; this skill owns the medium, never the message.

## 1. Locate the content

Ask which approved artefact this renders. A microsite is a presentation layer
over findings that already exist and have already been reviewed.

- If the engagement is set up, resolve paths through `99 - AI System/engagement.yaml`.
- The finished deliverable belongs in `09 - Final Deliverables`.
- **Never invent a finding, a number, or a recommendation to fill a template.**
  An empty section is a question for the consultant, not a gap to paper over.

If the source material is thin, say so and stop. A readout with three
half-evidenced themes is worse than a readout with one solid one.

## 2. Choose the archetype

Read `archetypes.md`. Confirm the archetype's shape actually fits the material
before drafting — an executive readout that has no recommendations is not an
executive readout.

## 3. Draft `content.yaml`

Transcribe the source artefact into the content contract (`content-contract.md`).
Then **show the draft to the user and get confirmation.** This is the editorial
checkpoint. Correcting a sentence here costs nothing; correcting it after the
build means rebuilding, and correcting it after handoff means a new version.

For every client-facing deliverable, perform a whole-deliverable polish pass
before showing the draft. This applies to every current and future template or
archetype. Treat every visible title, eyebrow, metric, label, source line,
finding, recommendation, roadmap item, and closing action as client-ready.
Check spelling, punctuation, grammar, capitalization, terminology, and whether
the wording is suitably formal for the stated audience. Follow the active brand
pack's sentence-case standard unless the consultant confirms a different
treatment for a specific element. Do not expose internal workflow labels or
casual shorthand to the reader. Use standard American English in all
client-visible generated copy unless the consultant or client requests a
different convention; preserve verbatim source quotations when fidelity matters.

Two things to push on while drafting:

- **Every finding needs an implication.** If the source has theme and evidence
  but no so-what, ask for it. The schema will refuse the build otherwise, and
  it is right to.
- **Every number needs a source.** An unsourced figure in a client deliverable
  is a liability, so `source` is required on every KPI.

## 4. Confirm accent and motion

- One secondary colour, chosen from cyan, coral red, purple, chartreuse. Ask;
  do not assume. Client context often decides it — avoid a colour that clashes
  with the client's own brand, and avoid coral red where the readout is
  positive.
- Motion defaults to the archetype's documented level. Offer the quieter option
  for a formal or regulated audience: an executive steering committee readout
  and a design-partner showcase do not want the same energy.

## 5. Build, then validate

```bash
node scripts/build.mjs path/to/content.yaml --out ./build/client-readout
```

The brand gate runs automatically as the final step. **Report its result
honestly, including warnings.** Two warnings always fire on a clean build and
both need a human decision, not a shrug:

- the Slalom Sans font files are in the output, which is a redistribution
  question (see `delivery.md`)
- the quote uses a Slalom Sans–only treatment, because no serif ships with this
  repo

If the gate fails, fix the cause. Never pass `--no-validate` on anything headed
for a client; it exists for mid-edit iteration only.

## 6. Review it yourself before handing it over

The gate checks what a machine can check. Then look at it:

```bash
cd build/client-readout && python3 -m http.server 8000
```

- Scroll it once. Animations fire once, on entry, and nothing is stuck invisible.
- Turn on the OS "reduce motion" setting and reload. Everything visible, at rest.
- Print to PDF. No blank page, no clipped section, no half-counted number.
- Tab through it. Focus visible and in order.

## 7. Hand off

Follow `delivery.md`: where the file goes, the confidentiality marker, the font
licensing note, and `--bundle` when the deliverable has to travel by email.

## Iterating

Never hand-edit the built output. Change `content.yaml` and rebuild — the build
wipes and rewrites the output directory, so any manual edit is lost silently,
which is the safest failure mode available.

If a change cannot be expressed in the content contract, that is a signal about
the kit, not about the content: extend a component or add an archetype
(`component-kit.md`, `archetypes.md`), then rebuild.
