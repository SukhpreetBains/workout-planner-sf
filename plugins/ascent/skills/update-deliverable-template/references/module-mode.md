# Module mode

Create or modify one reusable content-domain module.

1. Establish the module's purpose, intended templates, information boundary,
   required questions, optional questions, and expected answer types.
2. Before creating a module, invoke `utilities-ui-generation` and read its
   branding guidance. Resolve the active brand pack, approved assets, color and
   typography rules, accessibility constraints, and established interaction
   conventions. Read its Anime.js guidance when the new module introduces or
   changes motion.
3. Inventory every existing `modules/<module-id>/module.json` and `html.mjs`,
   plus `modules/shared/primitives.mjs`. Compare the proposed information domain,
   questions, view structure, markup, interaction, and motion with what already
   exists.
4. Resolve overlap before adding files:
   - If the proposed information domain substantially matches an existing
     module, reuse or extend that module instead of creating a duplicate.
   - If an existing module contains a helper, control, layout, or complete
     visual composition that both modules need, extract the common
     implementation into appropriately scoped primitives in
     `modules/shared/primitives.mjs`. Update the original module and the new
     module to compose those primitives.
   - Keep each module's `module.json` and finished view registrations in its own
     folder. A local `html.mjs` remains the ownership boundary and may adapt a
     shared implementation to that module's view IDs and semantics.
   - Do not extract code merely because it looks similar. Share it only when the
     behavior, semantics, accessibility contract, and likely change cadence are
     genuinely common.
5. Give every question a stable module-prefixed ID. Keep canonical wording in
   the module. Templates may select questions or promote optional questions,
   but must not silently rewrite them.
6. Put the definition in `modules/<module-id>/module.json`. Give each
   output a module-local view ID, section type, explicit renderer path, and
   question mapping. Put every finished view registration in the `html.mjs`
   beside `module.json`, and reference it as `./html.mjs#<view-id>`. Reuse
   implementation through `modules/shared/primitives.mjs`, but do not register
   finished module views there. If composition is insufficient, explain why
   before adding a primitive, then update its schema, styles, motion, tests, and
   relevant template allowlists.
7. Use fictional content to render the module in isolation. Give the user a
   preview link and iterate until approved. Use the template's reviewed example
   content and pass `--preview-module <module-id>` to `build.mjs`.
8. Render the same module inside a representative template. Check neighboring
   sections, progress navigation, responsive behavior, reduced motion, print,
   JavaScript-disabled reading, and keyboard order. Obtain explicit approval.
9. Run the complete test and brand-validation suite. Report warnings honestly.
   Confirm that both the new module and every existing module affected by a
   shared extraction still pass isolated and in-context review.

Module definitions live in the authoritative
`create-deliverables/modules/` directory. Read the sibling
`create-deliverables/references/template-system.md` contract before editing.
