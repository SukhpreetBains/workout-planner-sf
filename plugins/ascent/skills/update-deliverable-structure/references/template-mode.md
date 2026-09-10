# Template mode

Create or modify one reusable microsite template.

1. Establish the audience, decision or session the template serves, required
   narrative shape, build defaults, and appropriate completion standard.
2. Compose an ordered series of existing modules. Invoke module mode first for
   any missing domain.
3. Build the complete example with `build.mjs --preview-template <name>`. Show
   the labeled module preview to the user and explain that they can choose which
   modules to include in their output. Confirm the intended starting composition.
4. Select module questions, promote optional questions only when the template
   truly cannot succeed without them, and define explicit output-mapping
   overrides only where the module default is not suitable.
5. Declare one `static_example` in the template manifest. Create realistic
   fictional content for every selected module in that file, plus a resumable
   intake example. Modules do not own fictional examples. Never embed real
   client facts in shared template assets.
6. Test complete, partial, conflicting, missing, not-applicable, optional-skip,
   incomplete-override, and final-override intake behavior.
7. Render the complete fictional template and every visible gap state. Give the
   user preview links, iterate, and obtain explicit visual approval.
8. Run the complete test, repository, brand, accessibility, and delivery gates.
   Report warnings honestly.

Templates live in `create-deliverables/templates/<template-name>/`. Keep the
internal archetype field for compatibility unless the user explicitly approves
a migration.
