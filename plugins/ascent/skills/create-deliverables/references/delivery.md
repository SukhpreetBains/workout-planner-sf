# Delivery

What happens between a passing build and a client reading it.

## The gate

`scripts/validate-brand.mjs` runs automatically as the last step of every build.
**Errors block delivery (exit 1); warnings print and pass (exit 0).** Run it
again at any time:

```bash
node scripts/validate-brand.mjs build/client-readout
```

Two rules have commercial teeth. Neither is allowed to become a warning that
scrolls past unread.

- **Rule 22 — zero external references.** No `http(s)://` in any `src`, `href`,
  `url()`, or import specifier. No CDN, no font service, no analytics, no
  tracking pixel. A deliverable that phones home is a data question the client
  did not agree to, and it is an error, not a warning.
- **Rule 28 — the Slalom Sans files are in the output.** This one is a warning,
  because whether it is acceptable is a licensing decision, not a technical one.
  See below.

## Font licensing — resolve this before the first handoff

**Slalom Sans is proprietary and licensed to Slalom.** No licence file ships with
it. Using it in Slalom-produced work is fine. Handing a client a folder or an
archive that contains the `.woff2` files themselves — which is exactly what a
self-hosted static site is — is a redistribution question, and it is distinct
from:

- embedding the font in a PDF, or
- hosting the site on Slalom infrastructure and giving the client a link.

Until someone confirms the licence permits redistribution, treat rule 28 as a
real gate rather than noise, and prefer one of these three routes:

1. **Host it on Slalom infrastructure** and send a link. No font files leave.
2. **Send the PDF**, printed from the microsite. Fonts are embedded, not shipped.
3. **Confirm the licence**, then send the folder or the bundle.

`.otf` desktop fonts are never shipped on the web under any circumstances; the
validator errors on their presence.

Anime.js is MIT, and MIT requires the licence travel with the code. `LICENSE.md`
is copied next to the bundle on every build and the validator errors if it is
missing.

## Known brand deviations

Both warn on every relevant build. Surface them to the user rather than burying
them, and disclose them if the deliverable goes to a brand review.

**The quote has no serif.** Both approved quote pairings in the Slalom pack's
`typography.md` (`utilities-ui-generation/branding/packs/slalom/docs/typography.md`)
want a supporting serif, and no serif ships with this repo. The `quote`
component uses a Slalom Sans–only treatment instead: Regular for the quote,
Bold for the name, Light for the title. If a serif is added to that pack's
`assets/fonts/`, revisit this.

**The Slalom line is drawn.** `graphic-elements.md` asks for the Creative Library
vector files rather than a hand-drawn line, and those files are not in this repo.
The cover's line is a "bold single line" in the approved idiom, but it is not an
official vector. Swap it for the real artwork if the deliverable is
brand-reviewed.

## Confidentiality

`meta.classification` is required, appears on the cover **and** in the footer, is
written into a `<meta name="classification">` tag, and is checked in both places
by the validator. Write it the way the engagement's agreement writes it — usually
`Confidential — prepared for <Client>`.

Every build also carries `<meta name="robots" content="noindex, nofollow,
noarchive">`. That is a courtesy, not a control: if the deliverable is hosted
anywhere reachable, put real access control in front of it.

## Where it goes

If the engagement is set up, the finished deliverable belongs in
`09 - Final Deliverables`, with paths resolved through
`99 - AI System/engagement.yaml`. Keep the `content.yaml` with it — it is the
source, and the next version starts from it rather than from the HTML.

## Which output to send

| Route | Send | Notes |
|---|---|---|
| SharePoint / intranet hosting | the folder | Upload the whole directory. Every path is relative. |
| Email | `<deliverable-name>.html` | One self-contained file, ~380 KB. Its filename is a safe, lowercase form of `meta.title`. It is also the only output that opens correctly straight off disk, because browsers refuse to fetch ES modules over `file://`. |
| Formal record, or a client who wants paper | the PDF | Print from the microsite. Check it first — see below. |

Build the bundle with `--bundle`. It inlines the stylesheets, the motion layer,
Anime.js as a data URL in the import map, the images, and woff2 fonts only (the
woff fallback would double the payload of a file that has to travel by email).

## Before you hand it over

The gate checks what a machine can check. Then check what it cannot:

```bash
cd build/client-readout && python3 -m http.server 8000
```

1. Scroll it. Animations fire once, on entry. Nothing is stuck invisible.
2. Turn on the OS "reduce motion" setting and reload. Everything visible, at rest.
3. Print to PDF. No blank page, no clipped section, no half-counted figure.
4. Load it with JavaScript disabled. All content still readable.
5. Tab through it. Focus visible and ordered.

Then report the gate result honestly, warnings included. "Passed with two
warnings, both known deviations, here is what they are" is the useful sentence.
"Passed" on its own is not.
