# PhaseExplorer

A clickable roadmap: numbered phases joined by connectors that fill Slalom Blue up to the active phase; each phase opens a panel with its timing, title, sentence and outcomes. Author one `<section>` per phase with `data-label` and optional `data-meta`, a heading, paragraphs and one `<ul>`; `data-default` picks the opening phase. Without the script the sections read as a plain list.

Three to six phases. It is a tab set: arrow keys, Home and End move between phases, and each panel ends with a "Next" link. Done phases fill blue, the active one shows the secondary color in a blue frame with an underline, so state never relies on color alone.

## Markup

```html
<div class="sl-px" data-sl="phases" data-default="1" aria-label="Engagement phases">
  <section data-label="Discover" data-meta="Weeks 1–3"><h3>Listen to the people closest to the work</h3><p>Interviews, ride-alongs and a data audit.</p><ul><li>Stakeholder interviews</li><li>Current-state map</li></ul></section>
  <section data-label="Define" data-meta="Weeks 4–6"><h3>Agree on where you are going</h3><p>Shape the target state and business case together.</p><ul><li>Target-state vision</li><li>Prioritized backlog</li></ul></section>
  <section data-label="Deliver" data-meta="Weeks 7–10"><h3>Build the first release</h3><p>Ship a working slice with your team.</p><ul><li>MVP release</li><li>Success metrics</li></ul></section>
  <section data-label="Transition" data-meta="Weeks 11–12"><h3>Hand over with confidence</h3><p>Train, document and step back.</p><ul><li>Training</li><li>Run book</li></ul></section>
</div>
```
