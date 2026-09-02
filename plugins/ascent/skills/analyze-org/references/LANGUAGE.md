# Building the shared vocabulary

On the **first run** against an org, `analyze-org` works *with the user* to capture the org's **domain language** — the words the business and the team actually use — and writes them to `architecture/vocabulary.md` (next to `architecture.md`). Every feature file and every later suggestion then uses those exact terms. Consistent language is the whole point: the map should read in the team's words, not Salesforce's defaults.

This file is the **guide** for that collaboration. The output is a project-specific `vocabulary.md`, built from [`_vocabulary-template.md`](_vocabulary-template.md).

---

## Why a shared vocabulary

A Salesforce org's API names rarely match how the business talks. The same thing might be an `Account` in metadata, a "Member" to the business, and a "Customer" in half the Apex. Left implicit, every agent and every doc picks a different word and the map fragments.

The vocabulary fixes one term per concept, ties it to the underlying metadata, and lists the aliases to **avoid**. After that, feature files say "Member" (and link the term), never "Account / Customer / Contact" interchangeably.

## What goes in the vocabulary

Capture the **org's domain language**, not generic software terms. Good entries are:

- **Business names for objects/record types** — `Account` (RecordType = Individual) → **Member**.
- **Named processes / lifecycles** — the Opportunity→Order→Contract flow → **Enrollment**.
- **Naming-prefix meanings** — every `SVC_*` class is part of the **Service Layer**; `Billing_*` belongs to **Billing**.
- **Roles / personas** — who "the Advisor" or "the Ops team" is in terms of profiles/permission sets.
- **Status / stage jargon** — what "Active", "In Flight", or stage "S3" means to the business.

Leave out anything that's just the plain Salesforce term with no business-specific meaning.

## Term format

Each entry follows the same shape (see the template):

```markdown
**Member**
An `Account` with RecordType = `Individual`. The business never says "Account" for these.
_Maps to_: `Account` (RecordType `Individual`)
_Avoid_: Customer, Contact, Client.
```

- **Bold term** — the one canonical word the team uses.
- **Definition** — one or two plain sentences.
- **_Maps to_** — the concrete metadata (object, record type, prefix, flow, permission set) it corresponds to. This is what ties the vocabulary to the org.
- **_Avoid_** — the aliases that mean the same thing, so everyone stops using them.

## How to facilitate (first run)

Do this **after** you've retrieved metadata and identified the candidate features (so you can propose terms from real components), and **before** you write the feature files (so they're written in the agreed language).

1. **Propose, don't interrogate.** From the metadata, draft a starter list: the main object clusters, the obvious named processes, the naming prefixes you found. Show the user 5–15 proposed terms with your guessed definition and metadata mapping.
2. **Ask targeted questions** where the metadata is ambiguous:
   - "You have `Account` with two record types — does the business call these something other than Accounts?"
   - "Everything is prefixed `SVC_` — what do you call that layer?"
   - "Is the Opportunity→Order chain a named process internally?"
3. **Let the user rename, merge, drop, and add.** They own the words; you supply the metadata grounding. Record their corrections verbatim.
4. **Confirm the final list**, then write `architecture/vocabulary.md` from the template.

Keep it tight — aim for **8–20 terms**. A vocabulary nobody can hold in their head won't get used.

## Principles

- **One concept, one word.** If two words are in play, pick one and list the other under _Avoid_.
- **Every term maps to metadata.** A term with no `_Maps to_` is a business word floating free — either tie it down or drop it.
- **The user owns the words; you own the grounding.** Don't invent business names; surface candidates from metadata and let the team name them.
- **The vocabulary is the source of truth for naming.** When a feature file and the vocabulary disagree, the vocabulary wins — update the feature file.

## On refresh

The vocabulary is **hand-curated** — never regenerate it from scratch on a refresh. Read the existing `architecture/vocabulary.md`, propose only *additions* for new metadata you found, and confirm them with the user. Preserve every existing term and its `_Avoid_` list.
