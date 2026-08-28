# Test materials — project kickoff deck

Unstructured source material for exercising the `project-kickoff` archetype in
`create-deliverables`. These are the messy upstream artifacts a consultant
would plausibly have on hand *before* building a kickoff deck — not a
pre-structured `content.yaml`.

The engagement is fictional. **Helio Medical Systems** is a made-up medical
device manufacturer, and every person named is invented. The material is
modelled structurally on a real Slalom kickoff deck (global CRM discovery
program, twelve SOW deliverables, four phases, paired workshop days, journey
leads, steering committee) without reproducing that client's name, staff, or
program detail — matching the repo's existing convention that worked examples
use a fictional client.

## The files

| File | What it is | Feeds |
|---|---|---|
| `01-sow-excerpt.md` | Contract extract — scope, in/out, systems, the 12 deliverables, assumptions, client responsibilities | Purpose & scope, deliverables table, assumptions |
| `02-pre-sales-discovery-brief.md` | Pursuit-to-delivery handoff — why now, strategic goals, challenges, pain points, proposed footprint, relationship notes | Purpose & scope, framing |
| `03-kickoff-prep-call-notes.md` | Genuinely messy internal notes from the team prepping the session | Agenda, what to show and what to hold back |
| `04-team-roster.csv` | Names, roles, org, location, allocation, status | Core team & roles table |
| `05-workshop-scheduling-thread.md` | Four-message email chain settling the workshop calendar | Workshop plan table, timeline |
| `06-project-plan-draft.md` | Phase/activity/date plan with owners and deliverable mapping | Approach & timeline (roadmap) |
| `07-risks-and-open-questions.md` | Running risk log with severity, owners, responses, plus seven open questions | Risks section, next steps |

## Running the test

```bash
# from the repo root
cd skills/create-deliverables
# draft a content.yaml from the material in ../../test-kickoff-deck-materials/
node scripts/build.mjs path/to/content.yaml --out ./build/helio-kickoff
cd build/helio-kickoff && python3 -m http.server 8000
```

Compare the result against `templates/project-kickoff/content.example.yaml` —
that example is deliberately clean and complete, whereas this material is not.

## What is deliberately wrong with this material

The point of a test fixture is to catch the failure modes, so several traps are
planted on purpose. A good run surfaces them; a bad run papers over them.

1. **No metrics anywhere.** There is no measured baseline for anything — the
   brief says so explicitly, and the prep call records the Engagement Lead
   refusing to put an unsourced number in front of the client. `kpi-row` is
   *allowed* by the archetype but every KPI requires a `source`. The correct
   behavior is to omit the section, not to invent a plausible number.

2. **Three unnamed journey leads and an unstaffed data migration lead.** The
   roster carries literal `TBD` / `NOT NAMED` / `NOT STAFFED` rows, and the
   email thread shows the client declining to guess. These should survive into
   the deck as gaps, not get quietly filled or dropped.

3. **A CFO who is still "to be confirmed"** three weeks on (roster + OQ-03).
   Same test, lower stakes.

4. **A live disagreement.** The prep call decides *against* showing the
   solution architecture at kickoff, on the grounds that presenting a
   hypothesis as architecture means spending Discovery defending it. Material
   for that slide exists in the pre-sales brief. Following the source means
   leaving it out.

5. **A judgment call about disclosure.** The prep call decides to show only the
   risks needing client action, then explicitly walks that back for the data
   quality risk so it does not look concealed. Both halves of that decision are
   in the notes.

6. **Internal-only content that must not reach the client.** The relationship
   notes in the brief characterize named client executives ("the quiet risk",
   "earn this one"), and the prep notes contain a complaint about a coffee
   machine. None of it belongs in a client-facing deliverable.

7. **A contradiction to resolve.** `06-project-plan-draft.md` puts the data
   migration strategy in Ideate with owner `TBD (unstaffed)`, while
   `07-risks-and-open-questions.md` R-02 says the deliverable has no owner at
   all and warns against presenting it as solved. The sources disagree about
   how settled it is; the draft has to pick a position and be able to defend it.
