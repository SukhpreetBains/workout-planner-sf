# Timeline

A vertical timeline whose Slalom Blue rail draws itself down as each milestone scrolls in, stopping at the last marker. `data-date` on each item; `sl-tl-current` marks now, with a larger marker and a secondary-color label (`data-current-label`, default "Now"). On narrow screens the date moves above the title.

For a project's story, a history or a release plan. One title and one sentence per entry.

## Markup

```html
<ol class="sl-tl" data-sl="timeline">
  <li data-date="Jan 2026"><h3 class="sl-tl-title subhead">Kickoff</h3><p class="sl-tl-body body">Teams aligned on goals and success measures.</p></li>
  <li data-date="Mar 2026"><h3 class="sl-tl-title subhead">Pilot in two regions</h3><p class="sl-tl-body body">Field teams tested the new tool.</p></li>
  <li data-date="Jun 2026" class="sl-tl-current"><h3 class="sl-tl-title subhead">National rollout</h3><p class="sl-tl-body body">1,200 technicians moved onto the platform.</p></li>
  <li data-date="Q4 2026"><h3 class="sl-tl-title subhead">Predictive maintenance</h3><p class="sl-tl-body body">Models flag issues before customers notice.</p></li>
</ol>
```
