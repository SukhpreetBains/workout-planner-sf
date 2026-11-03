# Components

Framework-free HTML, CSS and JavaScript patterns for Slalom microsites and
HTML deliverables. Each one is built only from this pack's tokens, Slalom Sans
and approved assets, and follows the rules in `../docs/`. Open
`gallery.html` in a browser to see every pattern live, in Light and Dark.

These mirror the components in the Slalom design system on claude.ai, ported
from React to plain markup so deliverables need no framework.

## Load

Copy `slalom-components.css`, `slalom-components.js` and the pack's
`assets/fonts/` into the output, keeping `assets/` one level above the
stylesheet (or edit the `@font-face` paths at the top of the stylesheet).

```html
<head>
  <script>document.documentElement.classList.add('sl-js')</script>
  <link rel="stylesheet" href="components/slalom-components.css">
</head>
<body class="sl-tone-cyan">
  …
  <script src="components/slalom-components.js"></script>
</body>
```

- The inline `sl-js` line stops animated content from flashing before it
  hides. Without the script every pattern renders in its final, readable
  state, and print always shows final states.
- `sl-tone-cyan`, `-coral-red`, `-purple` or `-chartreuse` sets the
  composition's **one** secondary color for every pattern inside it. Set it
  once, on `<body>` or a section.
- `data-theme="dark"` on `<html>` or a section switches to the black-ground
  theme.
- Patterns with a `data-sl` attribute are enhanced by the script on load.
  For content added later, call `SlalomUI.init(container)`.
- Motion uses CSS transitions and IntersectionObserver. It needs no Anime.js;
  layer Anime.js (`../../../../references/animejs.md`) only for motion these
  patterns do not cover.
- Everything settles to its final state under `prefers-reduced-motion`.

## Catalog

Each file in `reference/` gives the pattern's purpose, options, rules and
markup.

| Group | Patterns |
| --- | --- |
| Brand | [Logo](reference/Logo.md), [ColorBar](reference/ColorBar.md), [ColorBarLoader](reference/ColorBarLoader.md), [Icon](reference/Icon.md), [IconCircle](reference/IconCircle.md), [ColorSelector](reference/ColorSelector.md), [SecondaryColorSelector](reference/SecondaryColorSelector.md) |
| Actions | [Button](reference/Button.md), [AnimatedButton](reference/AnimatedButton.md), [PushButton](reference/PushButton.md), [Link](reference/Link.md) |
| Forms | [Toggle](reference/Toggle.md), [Checkbox](reference/Checkbox.md), [MenuToggle](reference/MenuToggle.md) |
| Surfaces | [Card](reference/Card.md), [HoverCard](reference/HoverCard.md) |
| Typography | [Headline](reference/Headline.md), [PullQuote](reference/PullQuote.md) |
| Storytelling | [KineticHeadline](reference/KineticHeadline.md), [Reveal](reference/Reveal.md), [ChapterMarker](reference/ChapterMarker.md), [SplitHero](reference/SplitHero.md), [Marquee](reference/Marquee.md) |
| Data | [StatCounter](reference/StatCounter.md), [WaffleStat](reference/WaffleStat.md), [MetricBars](reference/MetricBars.md), [CompareSlider](reference/CompareSlider.md) |
| Navigation | [PhaseExplorer](reference/PhaseExplorer.md), [Timeline](reference/Timeline.md), [Accordion](reference/Accordion.md) |
| People | [ProfileCard](reference/ProfileCard.md), [QuoteCarousel](reference/QuoteCarousel.md) |

## Rules for every page

- One `SplitHero`, one `Marquee` and one `KineticHeadline` per page, and one
  color bar (a `ColorBarLoader` counts as one).
- Reveal-on-scroll paces a page; it never hides content a reader needs.
- Numbers, quotes, names and photos must be real, sourced and approved. The
  names and figures in `gallery.html` are placeholders.
- Pattern classes are prefixed `sl-`; do not restyle them with off-palette
  colors, extra rounded corners, gradients or shadows. Compose new layouts
  around them instead.
- `AnimatedButton`, `ColorBarLoader`, `HoverCard`, `MenuToggle`, `PushButton`,
  `Checkbox` and `ColorSelector` are adapted from Uiverse elements (MIT).
