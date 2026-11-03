# Icon

One approved icon from `../assets/iconography/` (index in its README) in one approved color. As an `<img>` it shows in Slalom Blue, the files' own ink. For Slalom Dark Blue, black or one secondary color, use `sl-icon-mask` with `--sl-icon` set to the file's `url()` and `background` set to the color token. Size between 48px and 240px. Give an `alt` or `aria-label` when the icon stands alone; leave it empty when the text beside it says the same.

One icon color per layout, Slalom Blue or Slalom Dark Blue preferred. Never reverse an icon light-on-dark, never use an icon from another set.

## Markup

```html
<img class="sl-icon" src="../assets/iconography/bar-chart.svg" alt="" width="64" height="64">
<span class="sl-icon-mask" role="img" aria-label="Results" style="--sl-icon:url('../assets/iconography/bar-chart.svg');--sl-icon-size:64px;background:var(--slalom-dark-blue)"></span>
```
