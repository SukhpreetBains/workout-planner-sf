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

If `codex plugin marketplace list` already includes `ascent`, skip the marketplace-add command. Relaunch the Codex app after installation so the plugin skills are loaded.

#### How Codex picks up changes

Codex keeps its own copy of the plugin. When the app launches, it compares
the version in `plugins/ascent/.codex-plugin/plugin.json` with that copy and
reinstalls only if the two differ. It does not look at file contents. So:

- a change reaches an installation only when it comes with a new version;
- an installation picks it up the next time the Codex app is relaunched —
  starting a new task is not enough.

While iterating on the local checkout, run:

```bash
python3 scripts/refresh_codex_plugin.py
```

On a feature branch, or with uncommitted changes, this gives the plugin a
new version, reinstalls `ascent@ascent` from the local marketplace, and
reminds you to relaunch Codex. Commit the version change together with your
plugin changes: that new version is what makes everyone else's installation
pick them up.

On a clean `main` checkout — how end users run Ascent — the same command
only pulls the latest release and asks for a relaunch. It never leaves a
local version edit behind, so it is safe for Codex to run when an end user
asks it to "update Ascent". If an older version of the script already left
such an edit, both this command and the background job restore it and carry on.

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
fast-forwards the local `main` checkout from `origin/main` once a day. The
update takes effect the next time Codex is relaunched; there is no need to
relaunch every time the job runs, since most runs find nothing new and one
relaunch picks up the latest download. When an update is waiting, Ascent's
workspace skills say so at the start of their next run. They also speak up
when background updates are stuck — blocked by macOS privacy settings, or no
successful check in ten days — and say why in plain words. It never prompts and
never forces a change — it skips safely (logging why, to
`~/.codex/ascent-plugin-update.log`) whenever the checkout is on another
branch or has uncommitted changes. The log also notes when a pull changed
plugin files without a new version, since Codex will not load those
changes. Decline or accept the
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

Update the clean repository checkout, then load the update in your host:

```bash
git pull --ff-only

# Codex: relaunch the Codex app. Nothing else is needed when the pull
# brought a new plugin version.

# Claude Code
claude plugin marketplace update ascent
claude plugin update ascent@ascent

# GitHub Copilot CLI
copilot plugin marketplace update ascent
copilot plugin update ascent
```

For the other hosts, start a new task or session after updating when the host does not reload plugin contents automatically. In Cursor, refresh the imported marketplace and update Ascent from the Plugins panel.
