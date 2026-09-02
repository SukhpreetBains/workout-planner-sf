# Ascent

Ascent is a self-contained, cross-host plugin for governed, evidence-backed
Discovery engagements and Opportunity delivery.

## Get the repository

Clone the repository into your normal project `repos/` directory, not an agent
host's managed plugin, cache, or skills directory. Reuse an existing checkout
instead of cloning another copy.

```bash
gh repo clone Slalom/ascent
cd ascent
```

## Install

Run the commands for the host you use from the repository root.

### Codex

```bash
codex plugin marketplace add .
codex plugin add ascent@ascent
```

If `codex plugin marketplace list` already includes `ascent`, skip the
marketplace-add command. Start a new Codex task after installation so the
plugin skills are loaded.

### Claude Code

```bash
claude plugin marketplace add .
claude plugin install ascent@ascent
```

If `claude plugin marketplace list` already includes `ascent`, skip the
marketplace-add command. Start a new Claude Code session after installation.

### GitHub Copilot CLI

```bash
copilot plugin marketplace add .
copilot plugin install ascent@ascent
```

If `copilot plugin marketplace list` already includes `ascent`, skip the
marketplace-add command. Start a new Copilot CLI session after installation.

### Cursor

For a personal setup, run the following command in Cursor and select Ascent:

```text
/add-plugin https://github.com/Slalom/ascent
```

For a team setup, import `https://github.com/Slalom/ascent` from **Dashboard >
Settings > Plugins > Team Marketplaces**, then grant the appropriate access.

## Update

Update the clean repository checkout before refreshing the plugin:

```bash
git pull --ff-only

# Codex
codex plugin add ascent@ascent

# Claude Code
claude plugin marketplace update ascent
claude plugin update ascent@ascent

# GitHub Copilot CLI
copilot plugin marketplace update ascent
copilot plugin update ascent
```

Start a new task or session after updating when the host does not reload plugin
contents automatically. In Cursor, refresh the imported marketplace and update
Ascent from the Plugins panel.

## Validate

```bash
python3 scripts/validate_collection.py
python3 -m unittest discover -s tests -v
```

The validation checks all 14 skills, all host manifests and marketplaces,
plugin assets, local references, and the absence of symlinks and hooks.
