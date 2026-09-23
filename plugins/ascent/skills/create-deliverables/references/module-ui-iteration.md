# Module UI iteration

Use this loop for a reusable module UI change. It keeps discovered evidence,
the authored data contract, and presentation work separate.

1. Keep the evidence and approval record in `intake.yaml` or `intake.json`.
   Do not add display-only fields to the intake to force a visual treatment.
2. Keep only client-provided presentation data in the module section of
   `content.yaml`. The module's `module.json` declares which intake questions
   each view uses.
3. Change the module-owned renderer (`modules/<id>/html.mjs`), component CSS,
   and behavior together. A renderer may reorganize, label, or disclose fields;
   it must not manufacture client facts.
4. Update `modules/<id>/example.json` with representative, fictional data.
   Every declared view must appear exactly once. This file is the stable visual
   fixture for UI review, not a discovery source.
5. Build only that module for fast visual iteration:

   ```bash
   node scripts/build.mjs --preview-module <module-id> --out build/<module-id>-isolated --bundle
   ```

6. Add or update a focused assertion in `scripts/test/run.mjs` for the UI's
   required hooks and contract behavior. Keep validation fixtures for minimal,
   long, dated, and undated data; these protect the renderer from making up
   schedule facts or depending on one happy-path payload.
7. Run the full test suite and review the brand gate before accepting the UI.

   ```bash
   node scripts/test/run.mjs
   ```

The resulting relationship is deliberate: discovery documents populate the
intake, the intake is resolved into `content.yaml`, and only the renderer turns
that contract into a module UI. The isolated preview provides a repeatable
design-review surface without making a generated client microsite the editable
source of truth.
