# SplitHero

The opening section of a microsite: a kinetic headline beside a photo that wipes open while a flat block of the secondary color settles in behind it, offset to the bottom right. The block takes the frame's corner class. Add `sl-hero-flip` to put the photo first; it stacks under 720px.

Once per page, at the top. Bright, candid, human photography: an approved asset from `../assets/photography/` or a real project photo, never stock standing in for a Slalom team member.

## Markup

```html
<section class="sl-hero" data-sl="hero">
  <div class="sl-hero-copy">
    <header data-sl="kinetic" data-highlight="momentum">
      <p class="sl-kh-eyebrow sl-eyebrow eyebrow">Data strategy</p>
      <h1 class="headline-xl">Turn your data into momentum</h1>
    </header>
    <p class="sl-hero-dek descriptor">A 12-week roadmap to put trusted data in the hands of every team.</p>
    <div class="sl-hero-actions"><a class="sl-btn sl-btn-primary" href="#">Explore the roadmap</a><a class="sl-btn sl-btn-secondary" href="#">Let’s talk</a></div>
  </div>
  <div class="sl-hero-media">
    <div class="sl-hero-frame sl-corner-br sl-radius-l"><img src="../assets/photography/horizon.jpg" alt="A horizon at sunrise"></div>
  </div>
</section>
```
