#!/usr/bin/env node
/**
 * Generate experimental HXL Mosaic fragments for guided template selection.
 *
 * The HXL host owns the `selection` data provider. Its submit action receives
 * a concise, machine-readable message whose values are HXL expressions.
 * This script does not add HXL to generated client microsites.
 */

import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const SKILL_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function readJson(file) {
  return JSON.parse(readFileSync(file, 'utf8'));
}

function templatePath(name) {
  if (typeof name !== 'string' || !/^[a-z0-9-]+$/.test(name)) {
    throw new Error(`template name must use lowercase letters, digits, and hyphens, found ${JSON.stringify(name)}`);
  }
  return path.join(SKILL_ROOT, 'templates', name, 'archetype.json');
}

export function loadHxlSelectorModel(templateName) {
  const selectedTemplate = readJson(templatePath(templateName));
  const templatesDir = path.join(SKILL_ROOT, 'templates');
  const templates = readdirSync(templatesDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => {
      const manifest = readJson(path.join(templatesDir, entry.name, 'archetype.json'));
      return { id: manifest.name ?? entry.name, title: manifest.title };
    })
    .sort((left, right) => left.id.localeCompare(right.id));
  const modules = selectedTemplate.modules.map(({ id }) => {
    const module = readJson(path.join(SKILL_ROOT, 'modules', id, 'module.json'));
    return { id: module.id, title: module.title };
  });
  return {
    template: { id: selectedTemplate.name ?? templateName, title: selectedTemplate.title },
    templates,
    modules,
  };
}

/**
 * Build the Mosaic surface. HXL's current public Select and Checkbox
 * support is experimental, so the host must retain the ordinary conversational
 * confirmation fallback described in SKILL.md.
 */
function previewAction({ kind, id, previewBase = null }) {
  if (previewBase) {
    return {
      definition: 'action/openLink',
      attributes: { url: `${previewBase.replace(/\/$/, '')}/${kind}/${id}/index.html` },
    };
  }
  return {
    definition: 'action/sendMessage',
    attributes: { content: `preview=${kind}; id=${id}` },
  };
}

function previewButton({ label, kind, id, previewBase }) {
  return {
    definition: 'tile/button',
    attributes: {
      label,
      variant: 'secondary',
      actions: { click: [previewAction({ kind, id, previewBase })] },
    },
  };
}

export function createHxlTemplatePicker({ previewBase = null } = {}) {
  const templates = loadHxlSelectorModel('project-kickoff').templates;
  return {
    definition: 'tile/column',
    attributes: { gap: 'lg' },
    children: [
      {
        definition: 'tile/text',
        attributes: { text: 'Choose a template', variant: 'h2' },
      },
      {
        definition: 'tile/select',
        attributes: {
          id: 'template',
          label: 'Template',
          placeholder: 'Select a template',
          isRequired: true,
          options: templates.map((template) => ({ label: template.title, value: template.id })),
        },
      },
      ...templates.map((template) => previewButton({
        label: `Preview ${template.title}`,
        kind: 'template',
        id: template.id,
        previewBase,
      })),
      {
        definition: 'tile/button',
        attributes: {
          label: 'Continue to modules',
          variant: 'primary',
          actions: {
            click: [{
              definition: 'action/sendMessage',
              attributes: { content: 'template={!$selection.template}' },
            }],
          },
        },
      },
    ],
  };
}

export function createHxlModulePicker(templateName, { previewBase = null } = {}) {
  const model = loadHxlSelectorModel(templateName);
  return {
    definition: 'tile/column',
    attributes: { gap: 'lg' },
    children: [
      {
        definition: 'tile/text',
        attributes: { text: `Choose modules for ${model.template.title}`, variant: 'h2' },
      },
      {
        definition: 'tile/text',
        attributes: {
          text: 'Select the modules you want to include before intake begins.',
          variant: 'body',
        },
      },
      previewButton({ label: `Preview ${model.template.title}`, kind: 'template', id: model.template.id, previewBase }),
      ...model.modules.map((module) => ({
        definition: 'tile/column',
        attributes: { gap: 'sm' },
        children: [
          {
            definition: 'tile/checkbox',
            attributes: { id: `module-${module.id}`, label: module.title, value: true },
          },
          previewButton({ label: `Preview ${module.title}`, kind: 'module', id: module.id, previewBase }),
        ],
      })),
      {
        definition: 'tile/button',
        attributes: {
          label: 'Submit',
          variant: 'primary',
          actions: {
            click: [{
              definition: 'action/sendMessage',
              attributes: {
                content: 'template={!$selection.template}; modules={!$selection.modules}',
              },
            }],
          },
        },
      },
    ],
  };
}

function parseArgs(argv) {
  const [mode, ...args] = argv;
  let templateName = null;
  if (mode === 'module-picker') templateName = args.shift();
  let out = null;
  let previewBase = null;
  for (let index = 0; index < args.length; index += 1) {
    if (args[index] === '--out') out = args[++index];
    else if (args[index] === '--preview-base') previewBase = args[++index];
    else throw new Error(`unknown argument ${JSON.stringify(args[index])}`);
  }
  if (mode === 'template-picker') return { mode, out, previewBase };
  if (mode === 'module-picker' && templateName) return { mode, templateName, out, previewBase };
  throw new Error('usage: node scripts/generate-hxl-selector.mjs template-picker | module-picker <template-name> [--preview-base url] [--out path]');
}

function isMain() {
  return process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
}

if (isMain()) {
  try {
    const { mode, templateName, out, previewBase } = parseArgs(process.argv.slice(2));
    const fragment = mode === 'template-picker'
      ? createHxlTemplatePicker({ previewBase })
      : createHxlModulePicker(templateName, { previewBase });
    const result = `${JSON.stringify(fragment, null, 2)}\n`;
    if (out) {
      mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
      writeFileSync(out, result);
    } else {
      process.stdout.write(result);
    }
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  }
}
