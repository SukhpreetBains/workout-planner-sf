# KineticHeadline

A hero headline whose words rise out of a mask one after another, then a block of the composition's secondary color wipes in behind the words named in `data-highlight` (one to three words, space-separated). Plays once, when it scrolls into view. Screen readers hear the whole headline once.

Use it for the one headline that opens a page or chapter, not every heading. Highlighted text turns black on the secondary color, so it reads in both themes. Without the script it is a normal headline.

## Markup

```html
<header data-sl="kinetic" data-highlight="together">
  <p class="sl-kh-eyebrow sl-eyebrow eyebrow">Our approach</p>
  <h1 class="headline-xl">Better tomorrows, built together</h1>
  <p class="sl-kh-dek sl-dek body">We help people and organizations dream bigger, move faster, and build better tomorrows for all.</p>
</header>
```
