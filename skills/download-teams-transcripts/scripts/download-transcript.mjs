#!/usr/bin/env node

import { spawn } from "node:child_process";
import { constants as fsConstants } from "node:fs";
import { access, mkdir, readFile, rename, unlink, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { createInterface } from "node:readline/promises";
import { fileURLToPath } from "node:url";

const HELP = `Usage:
  node download-transcript.mjs --meeting-title <title> [options]
  node download-transcript.mjs --recording-url <sharepoint-recording-url> [options]
  node download-transcript.mjs --url <sharepoint-stream-content-url> [options]

Inputs:
  --meeting-title <title>           Discover the recording in SharePoint by title and date
  --recording-url <url>             Verify Download and capture the transcript URL automatically
  --url <url>                       Use an already captured transcript streamContent URL

Required only with --url downloads:
  --confirm-download-authorized     Confirm the UI grants download permission

Options:
  --output <path>                   Output path (default: Call Transcripts in current project)
  --date <YYYY-MM-DD>               Meeting date (default: today in local time)
  --tenant-host <hostname>          Override the configured SharePoint host for this run
  --profile-dir <path>              Dedicated persistent Chrome profile
  --timeout-ms <milliseconds>       Page or sign-in timeout (default: 600000)
  --configure                       Run or repeat dependency and tenant setup
  --headless                        Run Chrome without a visible window
  --dry-run                         Validate input without opening Chrome
  --force                           Replace an existing output
  --help                            Show help
`;

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const STATE_DIR = path.join(os.homedir(), ".teams-transcript-downloader");
const CONFIG_PATH = path.join(STATE_DIR, "config.json");
const DEFAULT_PROFILE_DIR = path.join(STATE_DIR, "chrome-profile");
const SLALOM_TENANT_HOST = "twodegrees1-my.sharepoint.com";

const SHAREPOINT_SUFFIXES = [
  ".sharepoint.com",
  ".sharepoint.us",
  ".sharepoint.de",
  ".sharepoint.cn",
];

function parseArguments(argv) {
  const options = {
    timeoutMs: 600_000,
    dryRun: false,
    force: false,
    headless: false,
    confirmed: false,
    date: formatLocalDate(new Date()),
  };

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];

    if (argument === "--help") options.help = true;
    else if (argument === "--configure") options.configure = true;
    else if (argument === "--dry-run") options.dryRun = true;
    else if (argument === "--force") options.force = true;
    else if (argument === "--headless") options.headless = true;
    else if (argument === "--confirm-download-authorized") options.confirmed = true;
    else if (
      [
        "--url",
        "--recording-url",
        "--meeting-title",
        "--output",
        "--date",
        "--tenant-host",
        "--profile-dir",
        "--timeout-ms",
      ].includes(argument)
    ) {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) throw new Error(`${argument} requires a value.`);
      index += 1;
      if (argument === "--url") options.url = value;
      if (argument === "--recording-url") options.recordingUrl = value;
      if (argument === "--meeting-title") options.meetingTitle = value;
      if (argument === "--output") options.output = value;
      if (argument === "--date") options.date = value;
      if (argument === "--tenant-host") options.tenantHost = value;
      if (argument === "--profile-dir") options.profileDir = value;
      if (argument === "--timeout-ms") options.timeoutMs = Number(value);
    } else throw new Error(`Unknown argument: ${argument}`);
  }

  if (options.help) return options;
  const inputCount = [options.url, options.recordingUrl, options.meetingTitle].filter(Boolean).length;
  if ((!options.configure && inputCount !== 1) || (options.configure && inputCount > 1)) {
    throw new Error("Pass exactly one of --meeting-title, --recording-url, or --url.");
  }
  if (!Number.isInteger(options.timeoutMs) || options.timeoutMs <= 0) {
    throw new Error("--timeout-ms must be a positive integer.");
  }
  if (options.url && !options.dryRun && !options.confirmed) {
    throw new Error(
      "Pass --confirm-download-authorized only after Teams or SharePoint grants download permission.",
    );
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(options.date)) {
    throw new Error("--date must use YYYY-MM-DD format.");
  }
  if (options.tenantHost) options.tenantHost = validateTenantHost(options.tenantHost);
  return options;
}

function formatLocalDate(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseSharePointUrl(value, label) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`${label} is not valid.`);
  }

  if (url.protocol !== "https:") throw new Error(`${label} must use HTTPS.`);
  if (!SHAREPOINT_SUFFIXES.some((suffix) => url.hostname.toLowerCase().endsWith(suffix))) {
    throw new Error(`${label} must point to a Microsoft SharePoint host.`);
  }
  return url;
}

function validateRecordingUrl(value) {
  return parseSharePointUrl(value, "Recording URL");
}

function validateTenantHost(value) {
  if (!value || value.includes("://") || value.includes("/")) {
    throw new Error("Tenant host must be a SharePoint hostname without a path.");
  }
  return parseSharePointUrl(`https://${value}`, "Tenant host").hostname;
}

function validateTranscriptUrl(value) {
  const url = parseSharePointUrl(value, "Transcript URL");
  if (!url.pathname.includes("/_api/v2.1/drives/")) {
    throw new Error("Transcript URL must use the SharePoint drive API.");
  }

  const match = url.pathname.match(
    /\/items\/([^/]+)\/media\/transcripts\/([^/]+)\/streamContent$/i,
  );
  if (!match) throw new Error("URL does not identify a SharePoint transcript stream.");

  return {
    url,
    itemId: decodeURIComponent(match[1]),
    transcriptId: decodeURIComponent(match[2]),
  };
}

async function exists(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

function isInteractive() {
  return Boolean(process.stdin.isTTY && process.stdout.isTTY);
}

function assertNodeVersion() {
  const major = Number(process.versions.node.split(".")[0]);
  if (!Number.isInteger(major) || major < 20) {
    throw new Error(`Node.js 20 or newer is required. Current version: ${process.versions.node}.`);
  }
}

function runCommand(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, options);
    child.once("error", reject);
    child.once("exit", (code) => resolve(code === 0));
  });
}

async function askYesNo(question, defaultAnswer = false) {
  if (!isInteractive()) {
    throw new Error("Interactive first-run setup is required. Rerun in a terminal without --headless.");
  }
  const prompt = createInterface({ input: process.stdin, output: process.stdout });
  try {
    const suffix = defaultAnswer ? " [Y/n] " : " [y/N] ";
    const answer = (await prompt.question(`${question}${suffix}`)).trim().toLowerCase();
    if (!answer) return defaultAnswer;
    return answer === "y" || answer === "yes";
  } finally {
    prompt.close();
  }
}

async function ask(question) {
  if (!isInteractive()) {
    throw new Error("Interactive first-run setup is required. Rerun in a terminal without --headless.");
  }
  const prompt = createInterface({ input: process.stdin, output: process.stdout });
  try {
    return (await prompt.question(question)).trim();
  } finally {
    prompt.close();
  }
}

function chromeCandidates() {
  if (process.platform === "darwin") {
    return [
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
      path.join(os.homedir(), "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ];
  }
  if (process.platform === "win32") {
    return [
      process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, "Google/Chrome/Application/chrome.exe"),
      process.env["PROGRAMFILES(X86)"] &&
        path.join(process.env["PROGRAMFILES(X86)"], "Google/Chrome/Application/chrome.exe"),
      process.env.LOCALAPPDATA &&
        path.join(process.env.LOCALAPPDATA, "Google/Chrome/Application/chrome.exe"),
    ].filter(Boolean);
  }
  const pathCandidates = (process.env.PATH ?? "")
    .split(path.delimiter)
    .flatMap((directory) => ["google-chrome", "google-chrome-stable"].map((name) => path.join(directory, name)));
  return ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", ...pathCandidates];
}

async function findInstalledChrome() {
  for (const candidate of chromeCandidates()) {
    if (await exists(candidate)) return candidate;
  }
  return undefined;
}

async function importPlaywright() {
  try {
    return await import("playwright");
  } catch (error) {
    if (error?.code === "ERR_MODULE_NOT_FOUND" || error?.code === "MODULE_NOT_FOUND") return undefined;
    throw error;
  }
}

async function checkDependencies(offerInstall) {
  assertNodeVersion();
  console.log(`Dependency check: Node.js ${process.versions.node}`);

  const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";
  const hasNpm = await runCommand(npmCommand, ["--version"], { stdio: "ignore" }).catch(() => false);
  if (!hasNpm) throw new Error("npm is required. Install npm, then rerun this command.");
  console.log("Dependency check: npm found");

  const chrome = await findInstalledChrome();
  if (!chrome) {
    throw new Error("Google Chrome is required. Install Chrome from https://www.google.com/chrome/, then rerun this command.");
  }
  console.log(`Dependency check: Google Chrome found at ${chrome}`);

  let playwright = await importPlaywright();
  if (!playwright && offerInstall && isInteractive()) {
    const install = await askYesNo(
      `Playwright is not installed in ${SCRIPT_DIR}. Install the required package now?`,
      true,
    );
    if (install) {
      const installed = await runCommand(npmCommand, ["install"], {
        cwd: SCRIPT_DIR,
        stdio: "inherit",
      });
      if (!installed) throw new Error("npm install did not complete successfully.");
      playwright = await importPlaywright();
    }
  }
  if (!playwright) {
    throw new Error(`Playwright is required. Run npm install in ${SCRIPT_DIR}, then retry.`);
  }
  console.log("Dependency check: Playwright found");
  return playwright.chromium;
}

async function loadConfig() {
  try {
    const config = JSON.parse(await readFile(CONFIG_PATH, "utf8"));
    return { version: 1, tenantHost: validateTenantHost(config.tenantHost) };
  } catch (error) {
    if (error?.code === "ENOENT") return undefined;
    throw new Error(`Could not read setup config at ${CONFIG_PATH}: ${error.message}`);
  }
}

async function saveConfig(tenantHost) {
  await mkdir(STATE_DIR, { recursive: true, mode: 0o700 });
  await writeFile(CONFIG_PATH, `${JSON.stringify({ version: 1, tenantHost }, null, 2)}\n`, {
    mode: 0o600,
  });
}

function tenantHostFromInput(value) {
  if (!value) throw new Error("Enter a SharePoint hostname or URL.");
  if (value.includes("://")) return parseSharePointUrl(value, "SharePoint URL").hostname;
  return validateTenantHost(value);
}

async function promptForTenant(suggestedHost) {
  const useSlalom = await askYesNo(
    `Are you connecting to Slalom's SharePoint tenant (${SLALOM_TENANT_HOST})?`,
    true,
  );
  if (useSlalom) return SLALOM_TENANT_HOST;

  console.log("Open a recording, OneDrive file, or SharePoint page in the target organization.");
  console.log("Copy its full URL. The setup will extract and save only the SharePoint hostname.");
  if (suggestedHost) console.log(`A host was provided for this run: ${suggestedHost}`);

  while (true) {
    const value = await ask("Paste the SharePoint URL or hostname: ");
    try {
      return tenantHostFromInput(value || suggestedHost);
    } catch (error) {
      console.log(`Could not use that tenant: ${error.message}`);
    }
  }
}

async function prepareRuntime(options) {
  assertNodeVersion();
  const existingConfig = await loadConfig();
  const needsSetup = options.configure || !existingConfig;
  if (needsSetup && !isInteractive()) {
    throw new Error(
      `First-run configuration is required. Run node ${path.join(SCRIPT_DIR, "download-transcript.mjs")} --configure in an interactive terminal.`,
    );
  }
  const chromium = await checkDependencies(needsSetup || isInteractive());

  let configuredHost = existingConfig?.tenantHost;
  if (needsSetup) {
    configuredHost = await promptForTenant(options.tenantHost);
    await saveConfig(configuredHost);
    console.log(`Setup saved: ${CONFIG_PATH}`);
  }

  options.tenantHost = options.tenantHost ?? configuredHost;
  if (options.meetingTitle && !options.tenantHost) {
    throw new Error("A SharePoint tenant host is required for meeting discovery. Run with --configure.");
  }
  return chromium;
}

function safeFilename(value) {
  const cleaned = value
    .normalize("NFKD")
    .replace(/[<>:"/\\|?*\u0000-\u001F]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned || "meeting-transcript";
}

function defaultOutputPath(options) {
  const title = options.meetingTitle ? safeFilename(options.meetingTitle) : "meeting-transcript";
  return path.join(process.cwd(), "Call Transcripts", `${title} ${options.date}.vtt`);
}

async function ensureOutputDirectory(output) {
  const directory = path.dirname(output);
  if (await exists(directory)) return;
  if (!isInteractive()) {
    throw new Error(
      `Output folder does not exist: ${directory}. Create it first or rerun in an interactive terminal.`,
    );
  }
  const create = await askYesNo(`The output folder does not exist: ${directory}. Create it?`, true);
  if (!create) throw new Error("Output folder creation was declined. Provide another --output path.");
  await mkdir(directory, { recursive: true });
  console.log(`Created output folder: ${directory}`);
}

async function assertChromeLaunchAccess() {
  if (process.platform !== "darwin") return;

  const crashpadSettings = path.join(
    os.homedir(),
    "Library",
    "Application Support",
    "Google",
    "Chrome",
    "Crashpad",
    "settings.dat",
  );
  if (!(await exists(crashpadSettings))) return;

  try {
    await access(crashpadSettings, fsConstants.W_OK);
  } catch (error) {
    if (error?.code !== "EACCES" && error?.code !== "EPERM") throw error;
    throw new Error(
      "Google Chrome cannot start from this restricted shell because its Crashpad settings are not writable. Grant browser execution permission and retry the same command.",
    );
  }
}

async function chooseAvailableOutput(output, allowRename) {
  if (!(await exists(output))) return output;
  if (!allowRename) throw new Error(`Output already exists: ${output}`);

  const parsed = path.parse(output);
  for (let index = 2; index < 10_000; index += 1) {
    const candidate = path.join(parsed.dir, `${parsed.name} ${index}${parsed.ext}`);
    if (!(await exists(candidate))) return candidate;
  }
  throw new Error(`Could not choose an available filename in ${parsed.dir}.`);
}

async function openAuthenticatedPage(page, targetUrl, options) {
  const target = new URL(targetUrl);
  await page.goto(target.href, {
    waitUntil: "domcontentloaded",
    timeout: Math.min(options.timeoutMs, 60_000),
  });

  if (new URL(page.url()).hostname === target.hostname) return;
  if (options.headless) {
    throw new Error(
      "The dedicated Chrome profile is not signed in. Rerun without --headless and complete Microsoft sign-in once.",
    );
  }

  console.log("Complete Microsoft sign-in in the opened Chrome window.");
  await page.waitForURL((url) => url.hostname === target.hostname, {
    timeout: options.timeoutMs,
  });

  if (page.url() !== target.href) {
    await page.goto(target.href, {
      waitUntil: "domcontentloaded",
      timeout: Math.min(options.timeoutMs, 60_000),
    });
  }
}

function parseSearchRows(body) {
  const rows = body?.d?.query?.PrimaryQueryResult?.RelevantResults?.Table?.Rows?.results ?? [];
  return rows.map((row) => {
    const cells = row?.Cells?.results ?? [];
    return Object.fromEntries(cells.map((cell) => [cell.Key, cell.Value]));
  });
}

function matchesLocalDate(value, expectedDate) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return false;
  return value.startsWith(expectedDate) || formatLocalDate(parsed) === expectedDate;
}

function localDayNumber(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return undefined;
  return Date.UTC(parsed.getFullYear(), parsed.getMonth(), parsed.getDate()) / 86_400_000;
}

function dateDayNumber(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return undefined;
  return Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])) / 86_400_000;
}

function isWithinLocalDays(value, expectedDate, toleranceDays) {
  const actualDay = localDayNumber(value);
  const expectedDay = dateDayNumber(expectedDate);
  return actualDay !== undefined && expectedDay !== undefined && Math.abs(actualDay - expectedDay) <= toleranceDays;
}

function normalizedTitleTokens(value) {
  return value
    .normalize("NFKD")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
}

function containsTitleTokens(value, expectedTokens) {
  const candidateTokens = new Set(normalizedTitleTokens(value));
  return expectedTokens.every((token) => candidateTokens.has(token));
}

function isRecordingSearchRow(row) {
  return (
    row.FileExtension?.toLowerCase() === "aspx" &&
    row.Path?.includes("/Documents/Forms/DispForm.aspx")
  );
}

async function searchSharePoint(context, tenantHost, queryText, rowLimit = 50) {
  const search = new URL(`https://${tenantHost}/_api/search/query`);
  search.searchParams.set("querytext", `'${queryText}'`);
  search.searchParams.set("trimduplicates", "false");
  search.searchParams.set("rowlimit", String(rowLimit));
  search.searchParams.set(
    "selectproperties",
    `'Title,Path,FileExtension,LastModifiedTime,Created,ListId'`,
  );

  const response = await context.request.get(search.href, {
    headers: { Accept: "application/json;odata=verbose" },
  });
  if (!response.ok()) {
    throw new Error(`SharePoint recording search failed with HTTP ${response.status()}.`);
  }
  return parseSearchRows(await response.json());
}

async function findNearbyRecordingCandidates(context, meetingTitle, date, tenantHost) {
  const tokens = normalizedTitleTokens(meetingTitle);
  if (tokens.length === 0) return [];

  const queryText = tokens
    .map((token) => `Title:${token.replace(/["\\]/g, "")}*`)
    .join(" AND ");
  const rows = await searchSharePoint(context, tenantHost, queryText, 100);
  const candidates = rows
    .filter(
      (row) =>
        isRecordingSearchRow(row) &&
        containsTitleTokens(row.Title ?? "", tokens) &&
        isWithinLocalDays(row.Created, date, 1),
    )
    .sort((left, right) => new Date(right.Created) - new Date(left.Created));

  const resolved = [];
  for (const candidate of candidates.slice(0, 10)) {
    const recording = await resolveRecordingFile(context, candidate);
    if (recording) {
      resolved.push({
        title: candidate.Title,
        date: formatLocalDate(new Date(candidate.Created)),
      });
    }
    if (resolved.length === 5) break;
  }
  return resolved;
}

async function resolveRecordingFile(context, candidate) {
  const itemUrl = new URL(candidate.Path);
  const marker = "/Documents/Forms/DispForm.aspx";
  const markerIndex = itemUrl.pathname.indexOf(marker);
  const itemId = itemUrl.searchParams.get("ID");
  if (markerIndex < 0 || !itemId || !candidate.ListId) return undefined;

  const webPath = itemUrl.pathname.slice(0, markerIndex);
  const api = new URL(
    `${itemUrl.origin}${webPath}/_api/web/lists(guid'${candidate.ListId}')/items(${itemId})`,
  );
  api.searchParams.set(
    "$select",
    "File/ServerRelativeUrl,File/Name,File/TimeCreated,File/TimeLastModified",
  );
  api.searchParams.set("$expand", "File");

  const response = await context.request.get(api.href, {
    headers: { Accept: "application/json;odata=verbose" },
  });
  if (!response.ok()) return undefined;

  const file = (await response.json())?.d?.File;
  if (!file?.ServerRelativeUrl || !file?.Name?.toLowerCase().endsWith(".mp4")) {
    return undefined;
  }

  const recordingUrl = new URL(`${webPath}/_layouts/15/stream.aspx`, itemUrl.origin);
  recordingUrl.searchParams.set("id", file.ServerRelativeUrl);
  return { recordingUrl, file };
}

async function discoverRecordingUrl(context, meetingTitle, date, tenantHost) {
  const safeTitle = meetingTitle.replace(/["\\]/g, " ").trim();
  const expectedTitle = meetingTitle.trim().toLowerCase();
  const candidates = (await searchSharePoint(context, tenantHost, `Title:"${safeTitle}"`))
    .filter(
      (row) =>
        row.Title?.trim().toLowerCase() === expectedTitle &&
        isRecordingSearchRow(row) &&
        matchesLocalDate(row.Created, date),
    )
    .sort((left, right) => new Date(right.Created) - new Date(left.Created));

  for (const candidate of candidates) {
    const resolved = await resolveRecordingFile(context, candidate);
    if (resolved) {
      console.log(`Found recording: ${resolved.file.Name}`);
      console.log(`Meeting date: ${date}`);
      return resolved.recordingUrl;
    }
  }

  const nearby = await findNearbyRecordingCandidates(context, meetingTitle, date, tenantHost);
  if (nearby.length > 0) {
    console.log("Nearby recording candidates:");
    for (const candidate of nearby) {
      console.log(`- ${candidate.title} | ${candidate.date}`);
    }
    throw new Error(
      "No exact recording match. Retry with a listed calendar title and date, or pass --recording-url.",
    );
  }

  throw new Error(
    `No recording matched the exact indexed title "${meetingTitle}" and local date ${date} in ${tenantHost}. Retry with the calendar title, a nearby date, or pass --recording-url.`,
  );
}

async function captureTranscriptUrl(page, timeoutMs) {
  const transcriptPanel = page.getByRole("complementary", { name: "Transcript" });
  await transcriptPanel.waitFor({ state: "visible", timeout: Math.min(timeoutMs, 60_000) });

  const downloadButton = transcriptPanel.getByRole("button", {
    name: "Download",
    exact: true,
  });
  await downloadButton.waitFor({ state: "visible", timeout: Math.min(timeoutMs, 30_000) });
  if (!(await downloadButton.isEnabled())) {
    throw new Error("SharePoint does not grant transcript download permission.");
  }

  await downloadButton.click();
  const vttOption = page.getByText("Download as .vtt", { exact: true });
  await vttOption.waitFor({ state: "visible", timeout: Math.min(timeoutMs, 10_000) });

  const requestPromise = page.waitForRequest(
    (request) => {
      try {
        const url = new URL(request.url());
        return (
          url.pathname.includes("/media/transcripts/") &&
          url.pathname.endsWith("/streamContent")
        );
      } catch {
        return false;
      }
    },
    { timeout: Math.min(timeoutMs, 30_000) },
  );

  page.once("download", (download) => {
    void download.delete().catch(() => {});
  });
  await vttOption.click();

  const request = await requestPromise;
  return validateTranscriptUrl(request.url());
}

async function downloadTranscript(context, transcript, output, force, referer) {
  const response = await context.request.get(transcript.url.href, {
    headers: {
      Accept: "text/vtt, text/plain;q=0.9, */*;q=0.8",
      Referer: referer,
    },
  });

  if (!response.ok()) {
    throw new Error(`Download failed with HTTP ${response.status()}.`);
  }

  const contentType = response.headers()["content-type"] ?? "unknown";
  if (contentType.toLowerCase().includes("text/html")) {
    throw new Error("SharePoint returned HTML. The dedicated browser session may not be signed in.");
  }

  const content = await response.body();
  if (content.length === 0) throw new Error("SharePoint returned an empty transcript.");

  const text = content.toString("utf8").replace(/^\uFEFF/, "");
  if (!text.startsWith("WEBVTT")) throw new Error("SharePoint did not return WebVTT content.");

  const temporary = `${output}.part`;
  try {
    await writeFile(temporary, content, { mode: 0o600 });
    if (force && (await exists(output))) await unlink(output);
    await rename(temporary, output);
  } catch (error) {
    await unlink(temporary).catch(() => {});
    throw error;
  }

  const cueCount = (text.match(/-->/g) ?? []).length;
  console.log(`Saved: ${output}`);
  console.log(`Bytes: ${content.length}`);
  console.log(`Content-Type: ${contentType}`);
  console.log("WebVTT: true");
  console.log(`Cues: ${cueCount}`);
}

async function main() {
  const options = parseArguments(process.argv.slice(2));
  if (options.help) {
    console.log(HELP);
    return;
  }

  const chromium = await prepareRuntime(options);
  if (options.configure && !options.url && !options.recordingUrl && !options.meetingTitle) {
    console.log("Configuration complete.");
    return;
  }

  const directTranscript = options.url ? validateTranscriptUrl(options.url) : undefined;
  let recording = options.recordingUrl ? validateRecordingUrl(options.recordingUrl) : undefined;

  if (options.dryRun) {
    console.log(
      `SharePoint host: ${(directTranscript?.url ?? recording)?.hostname ?? options.tenantHost}`,
    );
    console.log(
      `Input: ${directTranscript ? "transcript stream" : recording ? "recording page" : "meeting search"}`,
    );
    console.log("Validation successful. No browser was opened.");
    return;
  }

  const usedDefaultOutput = !options.output;
  let output = path.resolve(options.output ?? defaultOutputPath(options));
  await ensureOutputDirectory(output);
  if (!options.force) output = await chooseAvailableOutput(output, usedDefaultOutput);

  await assertChromeLaunchAccess();

  const profileDir = path.resolve(
    options.profileDir ?? DEFAULT_PROFILE_DIR,
  );
  await mkdir(profileDir, { recursive: true, mode: 0o700 });

  const context = await chromium.launchPersistentContext(profileDir, {
    channel: "chrome",
    headless: options.headless,
    acceptDownloads: true,
  });

  try {
    const page = context.pages()[0] ?? (await context.newPage());
    let transcript = directTranscript;
    let referer;

    if (options.meetingTitle) {
      await openAuthenticatedPage(page, `https://${options.tenantHost}/`, options);
      recording = await discoverRecordingUrl(
        context,
        options.meetingTitle,
        options.date,
        options.tenantHost,
      );
    }

    if (recording) {
      await openAuthenticatedPage(page, recording.href, options);
      transcript = await captureTranscriptUrl(page, options.timeoutMs);
      referer = `${recording.origin}/`;
      console.log("Captured an authorized transcript request from the recording page.");
    } else {
      await openAuthenticatedPage(page, directTranscript.url.origin, options);
      referer = `${directTranscript.url.origin}/`;
    }

    console.log(`SharePoint host: ${transcript.url.hostname}`);
    console.log(`Drive item: ${transcript.itemId}`);
    console.log(`Transcript: ${transcript.transcriptId}`);
    await downloadTranscript(context, transcript, output, options.force, referer);
  } finally {
    await context.close();
  }
}

main().catch((error) => {
  console.error(`Error: ${error.message}`);
  process.exitCode = 1;
});
