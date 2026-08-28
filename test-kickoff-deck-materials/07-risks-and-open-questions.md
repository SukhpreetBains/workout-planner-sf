# Risks, issues & open questions — running log

**Owner:** Ingrid Halvorsen
**Last reviewed:** 4 September 2026
**Cadence:** reviewed weekly at the leads sync

Severity: H / M / L. Status: Open / Mitigating / Closed.

---

## Risks

### R-01 — System access not confirmed for end of week 1
**Severity:** High · **Status:** Open · **Owner:** Rajiv Anand (Helio)
**Raised:** 26 Aug

SOW assumption A-04 commits Helio to providing read access to current-state
systems, including a representative data extract, by end of week 1. Rajiv has
not confirmed that date and has indicated the security review for third-party
read access "usually takes three weeks."

**Impact:** Current-state architecture and data quality work cannot start.
Learn phase compresses against a fixed end date. If access slips past week 3,
deliverables #7, #8 and #9 are all at risk.

**Response:** Farrah to raise directly with Marta Kovač, framed as a
sponsor-level unblock rather than an IT process complaint. Requesting a named
date at kickoff. Fallback is a scoped read-only extract for the two highest
priority systems rather than full estate access.

---

### R-02 — Data migration lead not staffed
**Severity:** High · **Status:** Mitigating · **Owner:** Ingrid Halvorsen
**Raised:** 28 Aug

Open requisition. Needed on the plan by week 3.

**Impact:** Deliverable #8 (Data Migration Strategy) has no owner. It is a
contracted deliverable with a client sign-off gate.

**Response:** Escalated to staffing 28 Aug, re-raised 2 Sept. Kenji can hold
the analysis groundwork for two weeks but is not the right level to own the
strategy or present it to Rajiv. Do not present this as solved at kickoff —
it is a Slalom-side commitment we have not yet met.

---

### R-03 — Data quality is unmeasured
**Severity:** High · **Status:** Open · **Owner:** unassigned
**Raised:** 1 Sept (kickoff prep call)

Every stakeholder interviewed during the pursuit asserted that data quality is
poor. No assessment has ever been run. There is no baseline.

**Impact:** Migration scope and effort cannot be sized. Any estimate in
deliverable #6 or #8 rests on an assumption nobody has tested. This is the
kind of unknown that surfaces in build and doubles a phase.

**Response:** Propose a lightweight data quality assessment in weeks 2–3.
Not currently on the plan and not in the SOW deliverable list, so it needs
either an agreed swap or a change request. **Decision needed at or before
kickoff.**

---

### R-04 — Field service population not engaged
**Severity:** Medium · **Status:** Mitigating · **Owner:** Elspeth Doyle
**Raised:** 1 Sept

Sven Aaltonen (Repair Operations) was not part of the pursuit. Field service
carries the largest process change in the proposed footprint — work order
management, scheduling and dispatch, installed base — and has had the least
involvement.

**Impact:** Requirements gaps in the highest-change area, and a Steering
Committee member encountering the scope of change to his organization for the
first time in a room of thirty people.

**Response:** Farrah to brief Sven one-to-one before the kickoff. Elspeth to
pull the field service change-impact conversation forward from week 5 to
week 2.

---

### R-05 — Three journey leads unnamed
**Severity:** Medium · **Status:** Mitigating · **Owner:** Lena Fischer
**Raised:** 2 Sept

Large Deals, Demonstrations & Evaluations, and Commercial Support have no
named lead. Demos & Evaluations is the hardest — the process owner left in
June and the role has been covered informally since.

**Impact:** Workshops run without the person who can authoritatively say how
the process actually works. Output quality drops and requirements need
rework.

**Response:** Lena working it, target Friday 11 September (last point to
reshuffle the calendar without disrupting sequence). Grant may cover Large
Deals but is already carrying PM — not agreed, and Farrah has concerns.
Escalation path is Dr. Brandt.

---

### R-06 — Scope drift on the distributor portal
**Severity:** Medium · **Status:** Mitigating · **Owner:** Farrah Bishop
**Raised:** 1 Sept

Some client stakeholders believe the distributor portal for the eleven indirect
markets is in scope. It is explicitly excluded (SOW 1.2.1, assumption A-07).

**Impact:** Expectation gap that surfaces at the closeout gate, when it is
expensive.

**Response:** State in and out of scope verbally at kickoff, not only on a
slide. Repeat at the first Steering Committee.

---

### R-07 — Quarter close blackout
**Severity:** Low · **Status:** Mitigating · **Owner:** Grant Mueller
**Raised:** 3 Sept

Week of 12 October is Helio quarter close. Commercial teams unavailable.
Confirmed in writing by Lena.

**Impact:** No client-facing sessions that week. Already reflected in the
plan; the risk is that someone schedules into it later.

**Response:** Blackout marked on the shared calendar. Flagged to Grant and
Jonah as calendar owners.

---

## Open questions

| ID | Question | Owner | Needed by |
|---|---|---|---|
| OQ-01 | What are the success criteria for this program? Charter deliverable (#2) carries them but they do not exist yet. | Farrah / Lena | Week 2 charter session |
| OQ-02 | Is there any measured baseline for quote cycle time, case handling time, or data quality? Camille offered to pull what analytics has. | Camille Okafor | Week 2 |
| OQ-03 | Is Beatriz Salgado (CFO) confirmed on the Steering Committee, or not? Still showing "to be confirmed" three weeks on. | Lena Fischer | First Steering Committee |
| OQ-04 | Is MuleSoft the middleware, or is that just the existing footprint? SOW A-08 assumes reuse but it is unvalidated. | Sanjay / Rajiv | Week 4 |
| OQ-05 | MVP market scope is US and UK per A-05. Does Germany expect to be in MVP? Dr. Brandt's language in the pursuit suggested he assumes so. | Farrah / Dr. Brandt | Week 3 |
| OQ-06 | Who owns the data quality assessment if it is agreed — Slalom or Helio? | Ingrid / Rajiv | Kickoff |
| OQ-07 | Do we need a formal ways-of-working session, and if so when? Parked from the prep call. | Ingrid | Week 2 |
