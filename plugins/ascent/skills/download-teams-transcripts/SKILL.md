---
name: download-teams-transcripts
description: Discover, download, or export authorized Microsoft Teams meeting transcripts by meeting title and date, SharePoint recording page, or transcript streamContent URL using only the bundled Playwright script and its isolated Chrome profile. Use for today's or recent Teams transcripts, first-time tenant setup, and operation without Microsoft Graph permissions. Do not invoke Browser, Chrome, Teams, Outlook, SharePoint, or other external plugins or connectors.
---

# Download Teams Transcripts

Use `scripts/download-transcript.mjs` for setup, recording discovery, authorization checks, request capture, and verified download.

## Use only this skill

- Execute only this skill's bundled script through the shell.
- Do not invoke Browser, Chrome, Computer use, Teams, Outlook, SharePoint, Microsoft Graph, MCP apps, connectors, or other plugins.
- Do not search for or capture `streamContent` with another tool.
- If no URL is present, use `--meeting-title` and `--date` before asking for a recording link.
- Never inspect, print, copy, or persist cookies or access tokens.

## Complete first-run setup

On its first run, the script checks Node.js, npm, Google Chrome, and Playwright. It offers to install Playwright with `npm install` when needed. Ask the user before allowing any dependency installation.

Before starting a headless retrieval, check that the skill-local `scripts/node_modules/playwright` directory and `~/.teams-transcript-downloader/config.json` exist. A global Playwright installation does not satisfy this script. In a restricted environment, request write access for the skill's `scripts` directory before installation and for `~/.teams-transcript-downloader` before configuration.

The setup then asks whether to use Slalom's SharePoint tenant. If the answer is no, it explains how to open a recording, OneDrive file, or SharePoint page and paste its URL. The script extracts and saves only the SharePoint hostname.

Run first-time setup in an interactive terminal with a TTY:

```bash
node <skill-directory>/scripts/download-transcript.mjs --configure
```

Use `--configure` again to change the saved tenant. Configuration is stored in `~/.teams-transcript-downloader/config.json`. The isolated sign-in profile is stored separately in the same state directory and is never part of the shareable skill.

Require:

- Node.js 20 or newer
- npm
- Google Chrome
- Playwright from `scripts/package.json`

Do not bundle `scripts/node_modules`. Install dependencies locally when the user approves.

## Choose the output folder

Run the script from the project folder. When `--output` is omitted, save into `<project-folder>/Call Transcripts` with a title-and-date filename.

Resolve and approve the output folder before starting any browser retrieval. This prevents a missing folder from forcing a second Chrome launch after recording discovery.

- If `Call Transcripts` is missing, offer to create it and wait for the user's approval.
- If the user declines, ask for another output path and pass it with `--output`.
- Preserve existing files. The default output flow chooses a numbered filename when needed.
- Never save transcripts in the skill directory.

## Discover by title and date

Infer an exact recurring meeting title from conversation context and use the user's local date.

```bash
node <skill-directory>/scripts/download-transcript.mjs \
  --meeting-title '<meeting-title>' \
  --date '<YYYY-MM-DD>' \
  --headless
```

The script searches the configured SharePoint tenant, resolves the recording, verifies the enabled transcript Download action, captures the authorized transcript request, and downloads the WebVTT file. Exact title and local-date matching remains the safe default. When no exact match exists, the script searches normalized title tokens within one day and reports up to five nearby recording candidates without choosing one automatically.

Use `--tenant-host '<hostname>'` only to override the saved tenant for one run. If the meeting title is unknown, ask for it. Ask for a recording link only after title-and-date discovery fails.

## Use a recording page

When an exact SharePoint or OneDrive recording page URL is present, use it directly:

```bash
node <skill-directory>/scripts/download-transcript.mjs \
  --recording-url '<sharepoint-recording-url>' \
  --headless
```

The script verifies that the Transcript panel exposes an enabled Download action before capturing and downloading the transcript.

## Complete Microsoft sign-in

If headless mode reports that the isolated profile is not signed in, rerun the same command without `--headless`. Ask the user to complete Microsoft sign-in in the opened Chrome window. Reuse only the script's isolated profile.

## Use an existing transcript URL

For an existing SharePoint `streamContent` URL, validate it without opening Chrome:

```bash
node <skill-directory>/scripts/download-transcript.mjs \
  --url '<streamContent-url>' \
  --dry-run
```

Download only after Teams or SharePoint has shown that download is permitted:

```bash
node <skill-directory>/scripts/download-transcript.mjs \
  --url '<streamContent-url>' \
  --headless \
  --confirm-download-authorized
```

Use `--force` only when the user explicitly requests replacement. Use `--profile-dir` only for another isolated profile.

## Enforce authorization

- Treat view and download permissions as different permissions.
- Never bypass disabled downloads, Conditional Access, sensitivity labels, or tenant policy.
- Discard the browser's download and use only the verified authenticated request flow.
- Stop on HTTP 401 or 403, missing Download controls, or disabled Download controls.

## Verify without exposing content

Report only:

- Output path
- Byte count
- Content type
- WebVTT status
- Cue count

Do not print transcript lines.

## Handle failures

- Missing dependency: offer the documented installation only after user approval.
- Restricted macOS Chrome launch: if the script reports that Crashpad settings are not writable, rerun the same command with browser execution permission. Do not retry inside the restricted shell because Chrome will abort and macOS may report an unexpected close.
- Missing tenant setup: rerun with `--configure` in an interactive terminal.
- Not signed in while headless: rerun once without `--headless` for interactive sign-in.
- No exact recording found with nearby candidates: ask the user to confirm a listed calendar title and date, then retry once. Do not guess.
- No recording or nearby candidates found: verify the calendar title, nearby date, and configured tenant, then ask for the recording link.
- Transcript panel missing: confirm the correct recording has a completed transcript.
- Download missing or disabled: stop because the account lacks download permission.
- Request capture timeout: reload and retry once, then report a likely SharePoint UI or endpoint change.
- HTML response: report an expired or redirected authentication session.
