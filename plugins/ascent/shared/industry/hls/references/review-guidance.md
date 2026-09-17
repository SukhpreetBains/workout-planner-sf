# Health & Life Sciences — review guidance

Read alongside `workspace-review-updates`'s normal instructions. These are
additional things worth a reviewer's attention before approving a
proposed row — never a reason to change how the review mechanism itself
works.

## Check before approving

- **No PHI/PII in the row itself.** Tracker copies are plain text, widely
  readable by any agent working in the workspace. If a proposal's
  `Statement`, `Notes`, or evidence excerpt contains what looks like an
  actual patient or member identifier (name, MRN, date of birth tied to
  a specific person), stop and flag it rather than approving — this is
  worth raising with the user directly, not silently editing around.
- **Regulatory citations are accurate, not just present.** A finding that
  quotes HIPAA, a CMS rule, or an FDA regulation should be checked
  against what the source document actually says — a paraphrase that
  drifts from the original claim is worse than no citation at all.
- **Terminology matches this pack's vocabulary.** Prefer "EHR," "prior
  authorization," "PHI," etc. over generic phrasing when the row is
  describing something this vocabulary covers — it keeps the tracker
  readable to someone from the client's own organization.
- **Payer/provider/pharma attribution is correct.** When a stakeholder or
  system row identifies which side of the relationship it belongs to,
  confirm that's actually what the source evidence supports, not an
  assumption carried over from a similar-sounding earlier row.

None of this changes what "approve," "edit," or "reject" do — it's what
to look for while deciding between them.
