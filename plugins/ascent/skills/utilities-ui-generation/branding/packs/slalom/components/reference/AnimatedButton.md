# AnimatedButton

An outlined call to action: a Slalom Blue line in a 240 × 56 pill with tracked caps. On hover or focus the letter-spacing opens, the lines trade lengths and the secondary color's Light 3 tint pours in behind the text. Pick the tint with `sl-lbtn-cyan`, `-coral-red`, `-purple` or `-chartreuse` (the composition's one secondary). Works on `<a>` or `<button>`. After Uiverse `himanshu9682/wise-shrimp-26` (MIT).

Its pill is a deliberate exception to the one-rounded-corner rule: use one per view, for the hero or closing call to action, never in lists. Labels stay one to three words.

## Markup

```html
<a class="sl-lbtn sl-lbtn-cyan" href="#">
  <span class="sl-lbtn-line" aria-hidden="true"></span><span class="sl-lbtn-line" aria-hidden="true"></span>
  <span class="sl-lbtn-text">Let’s talk</span>
  <span class="sl-lbtn-drow1" aria-hidden="true"></span><span class="sl-lbtn-drow2" aria-hidden="true"></span>
</a>
```
