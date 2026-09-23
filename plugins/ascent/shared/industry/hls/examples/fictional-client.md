# Fictional client — Northstar Health

The one fictional client every HLS-flavored example, preview, or static
example should use, so worked examples across different templates and
modules don't contradict each other. Entirely fictional — never real
client information, per the base skill's non-negotiables.

Already used as the fictional client for the `weekly-status-report`
template's static example (`create-deliverables/templates/weekly-status-report/static-example.json`);
this profile expands on the same entity for use elsewhere in the HLS
pack, rather than inventing a second one.

## Profile

- **Northstar Health** — a regional integrated delivery network: a
  multi-hospital health system with an affiliated employed-physician
  group and a growing ambulatory/urgent-care footprint.
- Currently engaged with Slalom on **Care Access Modernization** — a
  program to modernize patient-facing access (scheduling, consent,
  identity/authentication) ahead of a broader EHR-integration phase.

## People

- **Dana Whitfield** — Sponsor (Northstar)
- **Morgan Reyes** — Client PM (Northstar)
- **Priya Anand** — Slalom Engagement Lead / PM
- **Theo Marsh** — Slalom Solution Architect
- **Jordan Blake** — Slalom Delivery Lead

## Representative workstreams

- Consent-capture flow redesign (patient-facing, precedes the identity
  provider integration)
- Identity provider contract and integration (blocks integration
  testing until signed — a recurring fictional risk/escalation across
  examples)
- Data-mapping review with Northstar's analytics team ahead of
  integration build
- Eventual EHR interoperability phase (FHIR-based), referenced as
  upcoming rather than in flight

## Using this profile

Reuse these names, roles, and workstream framing directly in any new
HLS-flavored fictional or preview content (a template's static example,
an isolated module preview, a worked illustration in a doc). Extend it
with additional fictional detail as needed, but keep the core identity
— who Northstar is, who these five people are, what Care Access
Modernization covers — consistent rather than reinvented per example.
