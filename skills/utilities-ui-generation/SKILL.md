---
name: utilities-ui-generation
description: UI-generation utilities for two related but independent needs, dispatched by task. Use for motion — adding animation to an HTML page or web app with Anime.js v4: entrances/reveals, hover and press micro-interactions, scroll-triggered effects, loaders, draggable UI, SVG line-drawing/morphing, animated text. Use for brand — applying or reviewing brand styling and voice across any deliverable medium (PowerPoint decks, PDFs, Word documents, spreadsheets, one-pagers, status reports, diagrams, dashboards, web experiences): colors, medium-specific typography, accessibility, voice, iconography, graphic elements, approved text/background combinations, and official asset usage, resolved from the currently active branding pack.
---

# UI Generation Utilities

Two independent utility references for UI-generation tasks, dispatched
by which one the task actually needs. They do not depend on each
other and are not sequential modes — read whichever applies, or both.

## Choose a reference

| Task | Read |
| --- | --- |
| Animation or motion — entrances/reveals, hover/press micro-interactions, scroll-triggered effects, loaders, draggable UI, SVG line-drawing/morphing, animated text | `references/animejs.md` |
| Brand styling or voice — colors, typography, accessibility, iconography, logos, graphic elements, imagery, writing style, messaging, across any medium | `references/branding.md` |

A single deliverable often needs both — build the visual/brand
composition per `references/branding.md`, then layer motion per
`references/animejs.md` if the task calls for it.

## Branding packs

`references/branding.md` and everything it points to reads from the
**active pack** under `branding/packs/<pack-name>/`, named in
`branding/active.json`. Slalom's own brand ships as the default pack,
`branding/packs/slalom/`. Deploying this skill library at a client
means adding `branding/packs/<client-name>/` with the same
`assets/` and `docs/` shape as `branding/packs/slalom/`, then pointing
`branding/active.json` at it — nothing else in this skill, and nothing
in `create-deliverables`, needs to change.

**What "hot-swappable" covers today, and what it doesn't**: swapping
the active pack changes which colors, fonts, logos, icons,
illustrations, and brand-voice guidance this skill and
`create-deliverables` read and copy. It does **not** yet change
`create-deliverables/scripts/validate-brand.mjs`'s enforcement rules —
that validator's palette, approved color pairings, font weights, and
copy checks are still hardcoded to Slalom's brand guide, so a
client-pack deliverable is still checked against Slalom's rules until
that validator is made pack-aware too. That is deliberately out of
scope here; treat it as required follow-up before deploying a
non-Slalom pack through `create-deliverables`.

## Dependents

`create-deliverables` resolves both utilities by relative path:
`../utilities-ui-generation/assets/animejs/vendor/` for the vendored
Anime.js bundle, and the active branding pack's `assets/` (resolved
via `branding/active.json`) for fonts, logos, icons, and
illustrations. Both are hard dependencies — its build fails with an
actionable message rather than emit a deliverable with a missing
asset.
