# Citation real-scenario checklist

For a dry run, use the [fictional unstructured working notes](fixtures/unstructured-kickoff-notes.md). Copy the file into an initialized test Opportunity's `workspace/inbox/`; do not run it in a live client workspace. For a real run, use one authorized meeting note, transcript, or narrative brief. Keep the original and record its exact path or URL.

1. Put the document in the project's `workspace/inbox/` and run `workspace-add`. Record the resulting source-ledger entry, filed original, proposal ID, exact quotation, and locator (line, timestamp, page, or section).
2. Review the proposal with `workspace-review`. Record whether it was approved, edited, or rejected. Only approved tracker rows can support a `source` citation.
3. In the create-deliverables intake, record the accepted answer and its source ID and locator. Compare the answer to the original passage; distinguish a paraphrased answer from an exact quote.
4. Author a section citation with the displayed value, accepted tracker row and field (`source_ref`), original document (`source_document`), precise `source_locator`, and exact `excerpt` if available. Add `source_url` only when readers can open it. If the displayed value diverges from the accepted evidence, use `changed` and explain the difference.
5. Build the deliverable and its bundle. Open **Sources** in the affected module. Check that the displayed value, document, locator, excerpt, and review record match steps 1–4 character for character. Open the original URL if one was supplied.
6. Repeat with a source that conflicts with the first and with an answer given directly by the user. Verify that conflict remains visible for review and that user input is labelled as such. Confirm that missing evidence never appears as verified.

The fictional note offers three checks:

| Passage | Expected treatment |
| --- | --- |
| Jordan's 30% contact-reduction target | Capture as a **target**, with the exact passage and original file locator. Do not call it an achieved result. |
| Theo's October 16 date and Priya's October 18 date | Surface the conflict for human review. Do not choose either date or mark an accepted date without a decision. |
| The mobile-app question | Keep as an open question. Do not infer that the pilot includes or excludes the app. |

Jordan's closing instruction is part of the document, so it is still **source evidence**, not a direct `user` answer to the agent. Test the `user` citation status only with an actual answer the user gives during the run.

Record results in a small table: scenario, original passage and locator, proposal, approved tracker field, intake answer, displayed value, source-panel text, and mismatch or gap. Do not put sensitive client source text in this repository or the fictional PR preview.

The pipeline is governed at the review step. The applied proposal in `workspace/.system/applied-updates/` retains its `evidence` passage and source path; use that record alongside the accepted tracker row when authoring the citation. The builder does not create citation entries automatically from intake answers, so step 4 is currently a manual mapping and an important place to look for drift. The first real run should expose whether that mapping needs a dedicated export or validator.
