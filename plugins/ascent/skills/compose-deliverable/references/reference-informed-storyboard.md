# Reference-informed storyboard

The authenticated Project Airhead executive-readout folder was inventoried on
August 28, 2026. This reference records structure only; it does not reproduce or
retain customer content.

## Source route

- `content.json` exists beside the published `site/` folder.
- The published site contains local HTML, CSS, JavaScript, fonts, a brand
  manifest, and an approved Slalom logo.
- The ordered readout types are summary, metrics, findings, recommendations,
  roadmap, next steps, and evidence base.
- The renderer should consume structured content. No general HTML importer is
  justified by this example.

## Proposed PowerPoint mapping

| Source section | PowerPoint treatment |
| --- | --- |
| Cover | One minimal cover slide |
| Summary | One leadership-takeaway slide |
| Metrics | One three-metric slide with visible sources |
| Findings | One slide per finding so evidence and implication remain readable |
| Recommendations | Two recommendations per slide |
| Roadmap | One three-phase comparison slide |
| Next steps | One numbered action slide |
| Evidence base | One method and source-boundary slide |

The synthetic demo produces 11 slides from this mapping. The storyboard covers
every source item exactly once and keeps the source order. Andrew and Gada still
need to approve the customer-specific slide story before customer content is
rendered.
