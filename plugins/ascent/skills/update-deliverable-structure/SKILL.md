---
name: update-deliverable-structure
description: Create or update reusable HTML templates and reporting briefs for the create-deliverables weekly status microsites.
---

# Update deliverable structure

Use for reusable template changes. One-off report refinements belong in the
project's generated output directory.

Read [create-deliverables](../create-deliverables/SKILL.md) and its
[weekly status brief](../create-deliverables/templates/weekly-status/brief.md).
Keep changes inside `create-deliverables/templates/weekly-status/` unless the
report input or asset copying also needs a corresponding update in `scripts/prepare.py`.
Keep the three sideways directions distinct and preserve the shared report fields
and six-page interaction contract.

Use the Slalom brand and Anime.js references from `utilities-ui-generation` for
styling and motion changes. Reuse the supplied assets. Keep sample content fictional.

Generate a fresh sample with `prepare.py`, run `create-deliverables/scripts/verify_assets.py`
against its output, check every option affected by the change, and provide preview
links for feedback. Verify input preservation, rendered image loading, responsive
layouts, navigation, print, and reduced motion. Use browser
checks only when allowed and state any verification gaps. Apply the repository's
plugin version and refresh process when shipping changes.
