# Brand — active pack dispatch

This reference applies brand styling and voice across any deliverable
medium (decks, PDFs, Word documents, spreadsheets, one-pagers, status
reports, diagrams, dashboards, web experiences) using whichever
**branding pack** is currently active.

## Find the active pack

Read `../branding/active.json` for the active pack's name, then read
that pack's own guide first: `../branding/packs/<pack>/docs/README.md`.
It has that pack's quick start, non-negotiables, "where to look"
table for its detail references, and asset index — everything below
is generic guidance for working with *any* pack, not pack-specific
rules.

Slalom's own brand ships as the default pack, `../branding/packs/slalom/`.

## Working with a pack

1. Identify the medium first — it decides the typeface and little
   else transfers between media. The active pack's own docs cover
   medium-specific rules.
2. Read only the pack's reference files the task touches. Each is
   single-topic and short.
3. Take artwork only from the active pack's `assets/`, never from an
   outside set and never from a different pack than the one that's
   active.
4. Check the result against the active pack's non-negotiables, or its
   `review-checklist.md` for a full review.

## Adding a new pack

A new pack is a new directory under `../branding/packs/<name>/` with
the same shape as `../branding/packs/slalom/`:

```text
branding/packs/<name>/
  assets/
    logos/
    iconography/
    illustrations/
    color-bars/
    fonts/
    branding-guide/          # optional — the source brand guide, if there is one
  docs/
    README.md                 # this pack's quick start, non-negotiables, asset index
    color.md
    typography.md
    accessibility.md
    logo.md
    graphic-elements.md
    imagery.md
    writing-style.md
    messaging.md
    creative-lens.md
    review-checklist.md
```

Populate it with the client's own approved assets and brand
guidance, then point `../branding/active.json` at it:

```json
{ "pack": "<name>" }
```

Consumers that explicitly request Slalom branding, including `create-deliverables`,
use the Slalom pack directly. Changing the active pack does not override that choice.
