# Planned Discovery AI Workflow

> Status: architecture stub; no phase coordinator is implemented.

```text
setup
  -> sales-handoff
  -> mobilize
  -> user-approved Mobilize completion
  -> discovery
  -> user-approved Discovery completion
```

`mobilize` and `discovery` will coordinate applicable specialist skills. Specialist skills will own their deliverables and validation. Coordinators must preview state-changing work, track status and gaps, and never mark work validated without user confirmation.

Mobilize and Discovery exit criteria are intentionally undefined. The user owns phase transitions until approved criteria are supplied.

Operational process design is deferred. `analyze-org` is reserved for Salesforce metadata architecture mapping and must not be repurposed as business-process analysis.
