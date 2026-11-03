# ProfileCard

A team member card: a portrait with one rounded corner, or a large monogram on the secondary color when there is no `<img>` (the script makes it from the name), with a Slalom Blue bio panel that slides up on hover. The script adds a "Read bio" button for touch and keyboard users.

Real photos of the real person only, never stock. Bios two sentences, third person, people-first. One tone for every card in a grid. The name above is a placeholder.

## Markup

```html
<article class="sl-pcard" data-sl="profile">
  <div class="sl-pcard-media sl-corner-br sl-radius-l"><div class="sl-pcard-bio body">Alex has led customer experience programs for 12 years and starts every project by riding along with frontline teams.</div></div>
  <div class="sl-pcard-meta"><h3 class="sl-pcard-name subhead">Alex Rivera</h3><p class="sl-pcard-title body-small">Engagement lead</p></div>
</article>
```
