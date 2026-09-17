# Health & Life Sciences — ingestion guidance

Read alongside `workspace-ingest-documents`'s normal instructions. This
never introduces a new tracker category or column — every finding still
goes through the same `risk` / `issue` / `stakeholder` / etc. categories
defined in `shared/schema/trackers.yaml`. It only shapes what to weight
and how to phrase what gets extracted.

## Weight these more heavily

- **Regulatory or compliance claims.** When a document cites a specific
  rule, statute, or standard (HIPAA, a CMS requirement, an FDA
  regulation, a specific FHIR version), quote it precisely in the
  evidence excerpt rather than paraphrasing — the exact citation is often
  the whole point of the finding.
- **PHI/PII sensitivity.** If a source document contains or references
  actual patient- or member-identifiable information, do not copy it
  into a proposed row's `Statement` or evidence excerpt. Summarize the
  nature of the finding without reproducing the identifying detail, and
  say plainly in the proposal that the source contains PHI so a
  reviewer knows to handle it carefully.
- **Interoperability specifics.** A mention of a specific standard,
  version, or integration engine (HL7 v2 vs. FHIR R4, a named HIE) is
  usually more useful to a downstream reader than "systems don't talk to
  each other" — extract the specific detail when the source gives one.
- **Payer/provider/pharma distinction.** When a stakeholder or system is
  described, note which side of the payer/provider/pharma relationship
  it sits on if the document makes that clear — it changes who owns a
  decision or risk.

## Classification hints

- Meeting material discussing clinical workflow changes, care
  coordination, or patient safety usually belongs to `risk` or `issue`
  with elevated severity — patient-safety-adjacent findings deserve the
  same scrutiny a security finding would get elsewhere.
- A document describing a regulatory submission, audit, or compliance
  deadline is `decision` or `open_question` territory as much as it is
  `risk` — who needs to decide what, by when, matters as much as the
  exposure itself.
- Don't infer PHI/PII handling requirements that a document doesn't
  actually state — flag it as an `open_question` for the client to
  confirm rather than asserting a compliance posture on their behalf.
