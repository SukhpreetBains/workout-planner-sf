# QuoteCarousel

One large quote at a time under an oversized Slalom Blue quotation mark, cross-fading to the next, with segment progress, a counter and square previous and next buttons. `data-interval` (ms, default 7000), `data-autoplay="false"` to stop autoplay. Autoplay pauses on hover and focus, the Pause button stops it, and it never autoplays under reduced motion. Without the script the quotes stack.

Two to five quotes, quoted exactly and attributed with permission. The names above are placeholders.

## Markup

```html
<section class="sl-qc" data-sl="quotes" data-interval="7000" aria-label="Customer quotes">
  <figure class="sl-qc-slide"><blockquote class="sl-qc-text">For the first time, our field teams and our data teams are looking at the same numbers.</blockquote><figcaption class="sl-qc-by"><span class="quote-name">Jordan Lee</span><span class="sl-qc-title quote-title">VP of operations</span></figcaption></figure>
  <figure class="sl-qc-slide"><blockquote class="sl-qc-text">They listened first. The plan felt like ours from day one.</blockquote><figcaption class="sl-qc-by"><span class="quote-name">Sam Okafor</span><span class="sl-qc-title quote-title">Chief people officer</span></figcaption></figure>
  <figure class="sl-qc-slide"><blockquote class="sl-qc-text">We shipped in ten weeks what we had been talking about for two years.</blockquote><figcaption class="sl-qc-by"><span class="quote-name">Maria Chen</span><span class="sl-qc-title quote-title">Head of digital</span></figcaption></figure>
</section>
```
