# Marquee

A slow band of short phrases looping across the page, separated by squares in the secondary color. Grounds: `sl-mq-accent` (Slalom Blue), `sl-mq-ink` (black), `sl-mq-surface` (white with hairlines). `--sl-mq-dur` sets seconds per loop (default 40); `sl-mq-reverse` flips direction. The script duplicates the list for a seamless loop and adds a Pause button that appears on hover.

One per page, as a breather between sections. It pauses on hover and focus; without the script or under reduced motion the phrases sit as a static row.

## Markup

```html
<div class="sl-mq sl-mq-accent" data-sl="marquee" aria-label="Capabilities" style="--sl-mq-dur:30s">
  <ul class="sl-mq-group"><li>Strategy</li><li>Data and AI</li><li>Customer experience</li><li>Modern engineering</li><li>Change that sticks</li></ul>
</div>
```
