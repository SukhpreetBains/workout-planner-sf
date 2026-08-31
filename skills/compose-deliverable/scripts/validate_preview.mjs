#!/usr/bin/env node

import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { pathToFileURL } from 'node:url';
import puppeteer from 'puppeteer';

function parseArgs(argv) {
  const options = { preview: null, manifest: null };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === '--manifest') options.manifest = argv[++index];
    else if (!options.preview) options.preview = argument;
    else throw new Error(`unexpected argument \`${argument}\``);
  }
  if (!options.preview || !options.manifest) throw new Error('usage: validate_preview.mjs <preview.html> --manifest <manifest.json>');
  return options;
}

function chromeExecutable() {
  const candidates = [
    process.env.CHROME_PATH,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ].filter(Boolean);
  return candidates.find((candidate) => existsSync(candidate)) ?? null;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const previewPath = path.resolve(options.preview);
  const manifest = JSON.parse(readFileSync(path.resolve(options.manifest), 'utf8'));
  const executablePath = chromeExecutable();
  if (!executablePath) throw new Error('Chrome or Chromium is required for preview overflow validation');
  const browser = await puppeteer.launch({ executablePath, headless: true });
  const externalRequests = [];
  try {
    const page = await browser.newPage();
    page.on('request', (request) => {
      if (/^https?:/i.test(request.url())) externalRequests.push(request.url());
    });
    await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
    await page.goto(pathToFileURL(previewPath).href, { waitUntil: 'networkidle0' });
    const report = await page.evaluate(() => {
      const slides = [...document.querySelectorAll('.slide')];
      return {
        slideCount: slides.length,
        problems: slides.flatMap((slide, slideIndex) => {
          const issues = [];
          const slideRect = slide.getBoundingClientRect();
          if (slide.scrollWidth > slide.clientWidth + 1 || slide.scrollHeight > slide.clientHeight + 1) {
            issues.push(`slide ${slideIndex + 1} content exceeds the fixed stage`);
          }
          const elements = [...slide.querySelectorAll('h1, h2, h3, p, li, blockquote, img')];
          for (const element of elements) {
            const style = getComputedStyle(element);
            if (style.display === 'none' || style.visibility === 'hidden') continue;
            const rect = element.getBoundingClientRect();
            if (rect.left < slideRect.left - 1 || rect.top < slideRect.top - 1
                || rect.right > slideRect.right + 1 || rect.bottom > slideRect.bottom + 1) {
              const label = (element.textContent || element.getAttribute('alt') || element.tagName).trim().slice(0, 70);
              issues.push(`slide ${slideIndex + 1} element is outside the stage: ${label}`);
            }
          }
          return issues;
        }),
      };
    });
    const problems = [...new Set(report.problems)];
    if (report.slideCount !== manifest.slides.length) {
      problems.push(`preview has ${report.slideCount} slides; manifest expects ${manifest.slides.length}`);
    }
    if (externalRequests.length) problems.push(`preview made external request(s): ${[...new Set(externalRequests)].join(', ')}`);
    if (problems.length) {
      for (const problem of problems) process.stderr.write(`FAIL: ${problem}\n`);
      process.exitCode = 1;
      return;
    }
    process.stdout.write(`PASS: fixed-stage preview (${report.slideCount} slides, no external requests or overflow)\n`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write(`Error: ${error.message}\n`);
  process.exitCode = 1;
});
