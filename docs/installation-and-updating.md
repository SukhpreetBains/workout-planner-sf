# Installing and updating Ascent

Ascent is installed from a clean local checkout of the repository. Keep that checkout in your normal project `repos/` directory, not in an agent host's managed plugin, cache, or skills directory. Reuse an existing checkout instead of cloning another copy.

## Get the repository

```bash
gh repo clone Slalom/ascent
cd ascent
```

## Install

Run the commands for your agent host from the repository root.

### Codex

```bash
codex plugin marketplace add .
codex plugin add ascent@ascent
```

If `codex plugin marketplace list` already includes `ascent`, skip the marketplace-add command. Start a new Codex task after installation so the plugin skills are loaded.

While iterating on the local checkout, refresh the installed Codex cache with:

```bash
python3 scripts/refresh_codex_plugin.py
```

This updates the Codex manifest cachebuster, reinstalls `ascent@ascent` from the local marketplace, and reminds you to start a new Codex task.

### Claude Code

```bash
claude plugin marketplace add .
claude plugin install ascent@ascent
```

If `claude plugin marketplace list` already includes `ascent`, skip the marketplace-add command. Start a new Claude Code session after installation.

### GitHub Copilot CLI

```bash
copilot plugin marketplace add .
copilot plugin install ascent@ascent
```

If `copilot plugin marketplace list` already includes `ascent`, skip the marketplace-add command. Start a new Copilot CLI session after installation.

### Cursor

For a personal setup, run the following command in Cursor and select Ascent:

```text
/add-plugin https://github.com/Slalom/ascent
```

For a team setup, import `https://github.com/Slalom/ascent` from **Dashboard > Settings > Plugins > Team Marketplaces**, then grant the appropriate access.

## Update

### Automatically (Codex, recommended for business users)

`initial-setup` offers to enable a daily background check the first time it
runs on a machine. If accepted, it registers a per-user scheduled job (a
macOS LaunchAgent, Windows Scheduled Task, or Linux crontab entry) that
fast-forwards the local `main` checkout from `origin/main` once a day and
refreshes the installed Codex plugin cache whenever that pull changes
anything. It never prompts and never forces a change — it skips safely
(logging why, to `~/.codex/ascent-plugin-update.log`) whenever the checkout
is on another branch or has uncommitted changes. Decline or accept the
question again at any time by rerunning `initial-setup`, or manage the job
directly:

```bash
python3 plugins/ascent/skills/initial-setup/scripts/manage-plugin-update-schedule.py --status
python3 plugins/ascent/skills/initial-setup/scripts/manage-plugin-update-schedule.py --install
python3 plugins/ascent/skills/initial-setup/scripts/manage-plugin-update-schedule.py --install --frequency weekly
python3 plugins/ascent/skills/initial-setup/scripts/manage-plugin-update-schedule.py --uninstall
```

`--install --frequency {daily,weekly}` also changes an already-installed
job's frequency in place — no need to uninstall first.

This only covers Codex. Claude Code, Copilot CLI, and Cursor still need the
manual steps below.

### Manually

Update the clean repository checkout before refreshing the plugin:

```bash
git pull --ff-only

# Codex
python3 scripts/refresh_codex_plugin.py

# Claude Code
claude plugin marketplace update ascent
claude plugin update ascent@ascent

# GitHub Copilot CLI
copilot plugin marketplace update ascent
copilot plugin update ascent
```

Start a new task or session after updating when the host does not reload plugin contents automatically. In Cursor, refresh the imported marketplace and update Ascent from the Plugins panel.
