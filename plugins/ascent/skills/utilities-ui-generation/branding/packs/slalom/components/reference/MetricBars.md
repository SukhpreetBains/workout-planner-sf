# MetricBars

Labelled horizontal bars that grow in turn once in view. `data-value` on each row; `data-max` on the list (default: the largest value — set 100 for percentages). `sl-mbar-hi` calls out one row: Slalom Dark Blue bar and a secondary-color value chip.

For ranked comparisons: maturity scores, survey results, adoption by team. Labels and values are always text, so nothing depends on color.

## Markup

```html
<ul class="sl-mbars" data-sl="bars" data-max="100">
  <li class="sl-mbar" data-value="38"><div class="sl-mbar-head"><span class="sl-mbar-label body-strong">Self-service analytics</span><span class="sl-mbar-value body-strong">38%</span></div></li>
  <li class="sl-mbar sl-mbar-hi" data-value="72"><div class="sl-mbar-head"><span class="sl-mbar-label body-strong">Trusted executive reporting</span><span class="sl-mbar-value body-strong">72%</span></div></li>
  <li class="sl-mbar" data-value="54"><div class="sl-mbar-head"><span class="sl-mbar-label body-strong">Automated data quality</span><span class="sl-mbar-value body-strong">54%</span></div></li>
</ul>
```
