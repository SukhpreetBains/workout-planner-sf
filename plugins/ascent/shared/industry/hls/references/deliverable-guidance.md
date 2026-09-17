# Health & Life Sciences — deliverable guidance

Read alongside `create-deliverables`'s normal instructions. This shapes
terminology, tone, and section emphasis within whichever template and
modules are already selected — it never selects a different template or
module set on its own, and every non-negotiable in the base skill
(especially: never invent a finding, number, owner, date, or decision)
applies with full force here, with extra weight given HIPAA's stakes.

## Terminology and tone

Draw wording from [vocabulary.md](vocabulary.md) rather than generic
consulting phrasing — "EHR," "prior authorization," "value-based care,"
"PHI" read as client-familiar; "the system," "the approval process,"
"outcomes-based pricing," "sensitive data" read as translated. Keep the
client's own vocabulary from source material wherever it was captured
that way in the trackers.

## Section emphasis

- **RAID / risk content**: call out regulatory and compliance risk
  explicitly, with the specific citation carried over from the tracker
  row, rather than folding it into a generic "risk" description.
- **Architecture / current-state content**: name interoperability
  standards explicitly (the FHIR version, the integration engine, the
  HIE involved) when the tracker rows behind it have that detail — don't
  flatten it to "systems are integrated."
- **Scope content**: be explicit about PHI/regulated-data boundaries —
  what's in scope for data access or handling, and what's deliberately
  excluded, if the reviewed evidence establishes that.
- **Stakeholder / governance content**: reflect the payer/provider/pharma
  distinction from the tracker rows rather than a generic RACI framing,
  when that distinction is what the evidence actually shows.

## Examples and previews

Use [examples/fictional-client.md](../examples/fictional-client.md) for
any fictional or preview composition — never blend real client PHI or
other identifying detail into example or draft content. This is the same
"never fabricate" rule the base skill already enforces everywhere else,
restated because the cost of getting it wrong is categorically higher
here than in a generic engagement.
