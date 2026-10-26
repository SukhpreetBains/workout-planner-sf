# Combined weekly status experiment

This implementation combines the lean, type-owned weekly status workflow from the current branch with section outlines and accepted-evidence inspection explored in [PR #70](https://github.com/Slalom/ascent/pull/70). It keeps the three Slalom presentations and their shared report data. It does not restore the older module system or adopt PR #70's scrolling shell.

## Editorial contract

Cover and summary stay first. The remaining pages follow the active outline, one section per page. The default outline has accomplishments, next steps, milestones, and combined risks with decisions. A user can approve additions, removals, and reordering. Save lasting choices at `workspace/.system/outlines/weekly-status.md`; a legacy `weekly-status-outlined.md` is read when the new file is absent. A reset uses the built-in outline without editing saved drafts.

Five layouts are supported: list, cards, timeline, table, and ask. The validator checks section names, layouts, tracker categories, inclusion and exclusion guidance, table columns, and card labels. Custom content is authored into the ordered `sections` array in `report.json`. Legacy report groups normalize into the default sections.

Current reviewed tracker rows govern facts about status, ownership, dates, decisions, and commitments. Accepted evidence excerpts show what supported a review at that time. Filed sources can clarify context, but cannot silently replace current reviewed values. Unresolved differences belong in the report's coverage note and the chat handoff. Missing evidence and documents remain visible as unavailable. Each cited local text document is copied as an escaped, bounded HTML snapshot under the output's `sources/` directory.

## Verification

Focused tests cover default and custom ordering, optional table and card layouts, legacy outline loading, invalid outline fields, malformed items, unknown tracker IDs, source selection, missing documents, escaping, and output asset packaging. Fictional default and custom packages live under `/private/tmp/combined-deliverables-preview/` for browser review. The custom package has a current tracker row, an accepted excerpt, and a portable source snapshot.

The source inspection design is adapted from PR #70's `link-sources.py`, and the outline fields and optional-section idea are adapted from its `outline.md` and `check-outline.mjs`. The resulting pipeline generates report data before rendering and uses the existing citation dialog in all three presentation styles.
