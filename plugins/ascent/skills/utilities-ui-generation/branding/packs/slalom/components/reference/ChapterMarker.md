# ChapterMarker

A chapter opener: a huge outlined number in Slalom Blue fills from the bottom up, then the title rises in and a rule in the secondary color draws across. `data-number` (2 becomes "02"). The script adds the number (hidden from screen readers) and "Chapter 02:" before the title for them.

Use one at the start of each major section of a long deliverable: current state, findings, recommendations, roadmap.

## Markup

```html
<div class="sl-chapter" data-sl="chapter" data-number="2">
  <div class="sl-chapter-body">
    <p class="sl-chapter-eyebrow eyebrow">Where we are today</p>
    <h2 class="sl-chapter-title headline-l">What we heard from your teams</h2>
  </div>
</div>
```
