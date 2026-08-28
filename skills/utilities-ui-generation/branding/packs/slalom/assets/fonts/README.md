# Fonts

**Slalom Sans is the only font family bundled here.** Read
[references/typography.md](../../references/typography.md) before setting type —
it owns the hierarchy, sentence-case, and leading/tracking rules, and it covers
the two brand typefaces that are *not* in this directory. This file only says
what is here and how to load it.

Two approved faces are deliberately absent:

- **Avenir Next LT Pro** is PowerPoint-only, plus Outlook defaults, Power BI, and
  editable Word docs shared with customers. It belongs to the approved
  PowerPoint template, never to a web page.
- **Lora**, the optional supporting serif, is not bundled. typography.md still
  describes it because it remains an approved brand face, but nothing in this
  repo can set it. Anything here that would call for a serif — either approved
  quote pairing, for instance — has to be composed in Slalom Sans alone, and the
  substitution disclosed. If a serif is added later, it goes here alongside its
  licence file.

## Slalom Sans

The primary font for all brand materials, including web. `Webfont Files/` for
anything in a browser; `Desktop Font Files/` for design tools and installed use.

| Style | Webfont | Desktop | CSS |
|---|---|---|---|
| Thin | `SlalomSans-Thin.woff2` · `.woff` | `SlalomSans-Thin.otf` | `100` normal |
| Thin Italic | `SlalomSans-ThinItalic.woff2` · `.woff` | `SlalomSans-ThinItalic.otf` | `100` italic |
| Light | `SlalomSans-Light.woff2` · `.woff` | `SlalomSans-Light.otf` | `300` normal |
| Light Italic | `SlalomSans-LightItalic.woff2` · `.woff` | `SlalomSans-LightItalic.otf` | `300` italic |
| Regular | `SlalomSans-Regular.woff2` · `.woff` | `SlalomSans-Regular.otf` | `400` normal |
| Italic | `SlalomSans-Italic.woff2` · `.woff` | `SlalomSans-Italic.otf` | `400` italic |
| Bold | `SlalomSans-Bold.woff2` · `.woff` | `SlalomSans-Bold.otf` | `700` normal |
| Bold Italic | `SlalomSans-BoldItalic.woff2` · `.woff` | `SlalomSans-BoldItalic.otf` | `700` italic |
| Black | `SlalomSans-Black.woff2` · `.woff` | `SlalomSans-Black.otf` | `900` normal |
| Black Italic | `SlalomSans-BlackItalic.woff2` · `.woff` | `SlalomSans-BlackItalic.otf` | `900` italic |

Each woff2 is 24–30 KB. There is **no Medium or SemiBold** — do not synthesize
one, and never let a browser fake a weight. Declare only the weights actually
loaded, and set `font-synthesis: none`.

Mapping the hierarchy in typography.md onto these weights:

| Role | Weight |
|---|---|
| Headline | `700` Bold; `900` Black when scale or message needs more force |
| Subhead | `700` Bold |
| Body | `300` Light; `400` Regular at small sizes or over busy backgrounds |
| Bullets | one step heavier than their text — `400` against Light body |

## Loading them

```css
@font-face {
  font-family: "Slalom Sans";
  src: url("slalom-sans-light.woff2") format("woff2"),
       url("slalom-sans-light.woff")  format("woff");
  font-weight: 300;
  font-style: normal;
  font-display: swap;
}

:root {
  --font-sans: "Slalom Sans", "Helvetica Neue", Arial, sans-serif;
}
```

Repeat the `@font-face` block per weight and style — one block each, never one
block listing several weights.

Two practical notes:

- **The directory names here contain spaces.** Copy fonts into a flat,
  space-free path in any output rather than pointing CSS at
  `slalom-sans/Webfont Files/`, which forces `%20` escaping and breaks in some
  tooling.
- Serve `woff2` first with `woff` as the fallback source, and skip the `.otf` on
  the web entirely.

Because the files are local and small, `font-display: swap` costs almost nothing
and avoids invisible text. If Slalom Sans is genuinely unavailable in some
context, typography.md requires you to preserve the hierarchy with a clean
sans-serif **and disclose the substitution**.

## Licensing

**Slalom Sans is proprietary and licensed to Slalom.** No licence file ships with
it. It is fine for Slalom-produced work. Before handing a client a folder or
archive that contains the font files themselves — as a self-hosted static site
would — confirm the licence permits that redistribution. Embedding the font in a
PDF, or hosting the site on Slalom infrastructure, is a different question from
shipping the woff2 files.
