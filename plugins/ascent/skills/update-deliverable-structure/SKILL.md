---
name: update-deliverable-structure
description: "Create or modify reusable create-deliverables modules and templates with overlap analysis, module-owned renderers, shared primitives, UI-generation review, tests, and iterative isolated and in-context visual approval."
---

# Update deliverable structure

Create reusable structure for `create-deliverables`. Use this skill only when
the user wants a customization promoted into a shared module or template, or
asks to create or change one directly. One-off microsite edits belong in a
detached deliverable package instead.

## Choose one mode

- **Module mode:** read [references/module-mode.md](references/module-mode.md).
- **Template mode:** read [references/template-mode.md](references/template-mode.md).

Before editing, inspect the repository instructions, current branch, and dirty
state. If the current branch is not suitable, ask whether to create a focused
branch and recommend a name. Preserve unrelated work.

Interview the user one decision at a time. For each question, recommend an
answer. Explore the codebase instead of asking questions it can answer.

Reuse existing components first. Add a component only when the intended module
cannot be expressed well with the current kit. Keep every structure generic and
reusable. Do not encode client facts in shared definitions or examples.

When creating a new module, invoke `utilities-ui-generation` before designing
or implementing its rendered views. Use its branding guidance to align the
module with the active brand pack, accessibility requirements, approved assets,
interaction conventions, and functional behavior. Use its Anime.js guidance
when the module adds or changes motion. This review is required for new modules,
even when the proposed view initially appears similar to an existing one.

Every new or changed structure must pass:

1. schema and intake validation
2. the full `create-deliverables` test suite
3. an isolated visual render
4. an in-context template render
5. brand and accessibility gates
6. explicit user approval of both visual renders

Do not call the work complete before visual approval. Provide preview links and
iterate on user feedback. Never register a module or template based only on
automated tests.
