# Module mode

Create or modify one reusable content-domain module.

1. Establish the module's purpose, intended templates, information boundary,
   required questions, optional questions, and expected answer types.
2. Search existing module definitions for overlap. Extend an existing module
   when the concepts are the same; create a new module when the domain is
   meaningfully distinct.
3. Give every question a stable module-prefixed ID. Keep canonical wording in
   the module. Templates may select questions or promote optional questions,
   but must not silently rewrite them.
4. Put the definition in `templates/modules/<module-id>/module.json`. Give each
   output a module-local view ID, section type, explicit renderer path, and
   question mapping. Reference `../shared/html.mjs` for reusable markup. Put an
   `html.mjs` beside `module.json` only when the markup is module-specific. If
   composition is insufficient, explain why before adding a renderer, then
   update its schema, styles, motion, tests, and relevant template allowlists.
5. Use fictional content to render the module in isolation. Give the user a
   preview link and iterate until approved. Use the template's reviewed example
   content and pass `--preview-module <module-id>` to `build.mjs`.
6. Render the same module inside a representative template. Check neighboring
   sections, progress navigation, responsive behavior, reduced motion, print,
   JavaScript-disabled reading, and keyboard order. Obtain explicit approval.
7. Run the complete test and brand-validation suite. Report warnings honestly.

Module definitions live in the authoritative
`create-deliverables/templates/modules/` directory. Read the sibling
`create-deliverables/references/template-system.md` contract before editing.
