---
name: recursive-improvement
description: Review mistakes and corrections after a workflow, identify reusable lessons, inspect applicable repository and AI-agent guidance across tools, and propose or apply improvements that prevent recurrence. Use after a failed, corrected, or inefficient workflow, or when asked to improve instructions, skills, rules, scripts, or operating guidance based on recent experience.
---

# Recursive Improvement

Review a completed or meaningfully paused workflow and turn its failures, corrections, and friction into durable improvements.

## Principles

- Remain agnostic to the AI tool, editor, agent runtime, and vendor.
- Use the evidence available in the current environment, such as conversation context, run logs, tool output, diffs, and user corrections. Do not assume every environment exposes the same history.
- Prefer root-cause fixes over instructions that merely describe a symptom.
- Respect instruction precedence, repository scope, user ownership, and approval requirements.
- Keep improvements concise and avoid duplicating existing guidance.

## 1. Catalog workflow issues

Identify each instance where:

- An initial attempt required correction
- A command, deployment, validation, or tool call failed and required a retry
- An assumption proved incorrect
- A file required a second edit because the first edit was wrong or incomplete
- The workflow created avoidable user prompts, side effects, or delays

For each issue, record:

- **What happened:** Describe the observable failure or friction.
- **Root cause:** Explain the underlying reason, including missing context, environment constraints, ambiguous guidance, or implementation defects.
- **Resolution:** State how the workflow recovered, or mark the issue unresolved.
- **Recurrence risk:** Classify it as one-off, environment-specific, repository-specific, tool-specific, or broadly reusable.

Do not classify expected external state, such as a genuinely missing record, as an agent mistake unless the workflow handled that state poorly.

## 2. Discover applicable guidance

Search for instruction sources that apply to the files and tools involved. Do not assume a single vendor-specific filename or directory. Read only relevant files, respecting their scope and precedence.

Common sources include:

- `AGENTS.md` files from the workspace root through the target file's directory
- `.github/copilot-instructions.md` and `.github/instructions/`
- `CLAUDE.md` and relevant `.claude/` guidance
- `.cursor/rules/` and `.cursorrules`
- `GEMINI.md`
- `.windsurf/rules/` and `.windsurfrules`
- Repository-neutral guidance such as `CONTRIBUTING.md`, development documentation, or documented operating procedures
- Relevant installed skills, plugins, extensions, scripts, or agent configuration when they are in scope and authorized for inspection

Treat this list as discovery guidance, not a requirement that every source exists. Do not read unrelated personal or global configuration outside the user's authorized scope.

For each issue, determine whether:

1. Existing guidance already covers it but is unclear or incomplete
2. No reusable guidance exists and one should be added
3. A script, template, validator, or skill should be improved instead of adding prose
4. The issue is specific to one AI tool and should remain in that tool's scoped guidance
5. The issue is broadly applicable and belongs in tool-neutral repository guidance
6. The issue is a one-off that does not justify a persistent change

## 3. Choose the smallest durable fix

Select the narrowest change that prevents recurrence:

- Update executable automation when deterministic handling is possible
- Update a reusable skill or extension when the workflow is specialized and repeated
- Update repository guidance when the lesson applies across contributors and tools
- Update tool-specific guidance only when the behavior depends on that tool
- Add an example when the rule is correct but easy to misinterpret

Avoid copying the same rule into multiple instruction systems. Prefer one authoritative, tool-neutral source when the repository already defines one.

## 4. Propose improvements

For each actionable improvement, provide:

- **Target:** File, script, skill, rule set, or configuration to change
- **Scope:** Tool-neutral, repository-specific, environment-specific, or tool-specific
- **Change type:** New instruction, clarification, implementation fix, new rule, skill update, or example
- **Proposed content:** Exact text or a precise implementation description
- **Evidence:** The workflow issue the change addresses

Ask for approval before applying changes unless the user has already explicitly authorized the update. If a change would broaden scope, affect external systems, or require a new material decision, request direction first.

## 5. Apply and verify

After approval:

1. Preserve user-owned changes and edit only approved targets.
2. Use the editing and validation mechanisms available in the active environment.
3. Validate in proportion to risk and follow repository rules about tests, builds, and external writes.
4. Re-read changed files and review the final diff or equivalent change summary.
5. Offer a documented repository-native sync, publish, or commit workflow only when it exists and the user authorizes it. Do not assume commands such as `syncgit` are available.

Report what changed, what was validated, and any remaining limitation.
