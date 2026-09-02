<!--
  TEMPLATE — copy to architecture/vocabulary.md (at the project root, next to architecture.md) and fill in.
  Built collaboratively with the user on first run — see LANGUAGE.md for how to facilitate.
  Replace every [placeholder]. Delete this comment block.
-->
# Shared Vocabulary — [org-alias]

> The org's domain language. Feature files and agent suggestions use these terms **exactly** — pick the bold word, avoid the listed aliases. Each term maps to the concrete metadata it names.
> Hand-curated: on refresh, terms are added with the user, never regenerated. See [`LANGUAGE.md`](LANGUAGE.md) for the format.

## Terms

**[Member]**
[One or two plain sentences — what the business means by this word.]
_Maps to_: `[Account]` ([RecordType `Individual`])
_Avoid_: [Customer, Contact, Client].

**[Enrollment]**
[The named process this term covers.]
_Maps to_: `[Opportunity]` → `[Order]` → `[Contract]` ([Flow `Enrollment_Flow`])
_Avoid_: [Signup, Onboarding].

**[Service Layer]**
[What this naming prefix / layer is.]
_Maps to_: Apex classes prefixed `[SVC_*]`
_Avoid_: [helpers, utils].

## Notes
<!-- manual — content below this line is preserved across refreshes -->
