<!--
  TEMPLATE — copy to architecture/features/<feature-slug>.md (at the project root) and fill in.
  Keep it tight: this is a map to the metadata, not full documentation.
  Use the org's words from ../vocabulary.md — name objects/processes by the team's term, with the
  API name in `code` for grounding (e.g. "Member (`Account`)"). Replace every [placeholder].
  Delete this comment block.
-->
# [Feature Name]

**Purpose**: [1–2 sentences — what business capability this feature delivers.]

**Entry points**: [How a user reaches it — app/tab/Lightning page, or "background automation only".]

## Data model

| Object | Role | Notable fields |
|--------|------|----------------|
| `[Obj__c]` | [parent / child / junction] | `[Field__c]`, `[Field2__c]` |

## Automation

| Component | Type | Triggers on / runs when |
|-----------|------|-------------------------|
| `[Name]Trigger` → `[Name]Handler` | Apex trigger | [after insert/update on Obj__c] |
| `[Flow_Api_Name]` | [record-triggered / screen / scheduled] | [condition] |
| `[ApexClass]` | [service / batch / controller] | [what it does] |

## UI

| Component | Type | Used on |
|-----------|------|---------|
| `[c-componentName]` | LWC | `[FlexiPage / record page]` |
| `[FlexiPage_Name]` | FlexiPage | `[Obj__c]` record page |

## Access

- **Permission set(s)**: `[PermSet_Name]` — [what it grants].

## Related features

- [Other Feature](other-feature.md) — [how they connect].

## Notes
<!-- manual — content below this line is preserved across refreshes -->
