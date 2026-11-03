---
name: utilities-ui-generation
description: "UI-generation utilities for two related but independent needs, dispatched by task. Use for motion: adding animation to an HTML page or web app with Anime.js v4, including entrances, reveals, hover and press micro-interactions, scroll-triggered effects, loaders, draggable UI, SVG line-drawing or morphing, and animated text. Use for brand: applying or reviewing brand styling and voice across deliverable media, including colors, typography, accessibility, voice, iconography, graphic elements, approved text and background combinations, and official asset usage resolved from the active branding pack."
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

`references/branding.md` resolves the active pack under `branding/packs/`.
Slalom ships at `branding/packs/slalom/`. Other consumers may select another
pack through `branding/active.json`.

The Slalom pack also ships framework-free web components at
`branding/packs/slalom/components/` — heroes, kinetic headlines, stat
counters, roadmaps, timelines, accordions, team cards and quote carousels,
plus buttons, cards and brand elements — with a live `gallery.html`. Use them
for microsites and HTML deliverables.

`create-deliverables` explicitly uses the Slalom pack for its weekly status
starters and copies the required fonts, logo, and illustrations into each output.
It also copies the pinned Anime.js bundle and license from `assets/animejs/vendor/`.
Its preparation helper checks these files before creating an output directory.
