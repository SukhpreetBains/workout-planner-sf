# Ascent

Ascent is an AI skill library for accelerated delivery of Discovery engagements. It gives Project teams a governed, evidence-backed path from source material to project knowledge and client deliverables.

The skills are host-neutral. Any supported agent host (Claude Code, Codex, Cursor, GitHub Copilot) uses the same flat library in `plugins/ascent/skills/`, distributed through the self-contained Ascent plugin.

See [Installing and updating Ascent](docs/installation-and-updating.md) to add the plugin to an agent host or refresh an existing installation.

## Install with an agent

Copy and paste this prompt into Codex, Claude Code, Cursor, or GitHub Copilot CLI:

```text
Install the Ascent plugin from https://github.com/Slalom/ascent for the agent host I am currently using. If the host is Codex, install it directly from GitHub with no local checkout: see docs/installation-and-updating.md for the exact commands. For any other host, reuse an existing clean local checkout if one is available; otherwise clone the repository into my normal project repos directory, not into an agent-managed plugin, cache, or skills directory, then follow docs/installation-and-updating.md from that checkout for the host-specific installation steps. Verify that the Ascent marketplace and plugin are installed, then tell me whether I need to start a new task or session so the skills load. Preserve unrelated files and existing work.
```

See the plugin-local [Ascent Workflow Overview](plugins/ascent/README.md) for the current setup handoff, knowledge lifecycle, and executable workflow boundaries. That overview is the shared workflow source for installed agents and repository readers.

## Repository layout

```text
plugins/ascent/   Self-contained plugin and authoritative skill library
docs/             Installation guidance and the full workspace walkthrough
evals/            Evaluation packages for the skills (contributor-facing)
tests/            Acceptance tests
```

Note that the Project workspace itself does **not** live in this repository. It lives in the Project's SharePoint folder, synced locally through OneDrive.

## Further reading

- [Installing and updating Ascent](docs/installation-and-updating.md), host-specific installation and update instructions.
- [Ascent Workflow Overview](plugins/ascent/README.md), the shared setup handoff and current knowledge lifecycle.
- [Project Workspace Walkthrough](docs/project-workspace-walkthrough.md), the complete setup and daily operating flow, step by step.
- [Ascent evaluations](evals/README.md), how skill evaluation packages are designed and run (for contributors).
