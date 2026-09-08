/** Template-owned instructions, visual choices, and decorative assets. */
import { readFileSync, realpathSync, copyFileSync, mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { BRANDING } from './assets.mjs';
import { ContentError } from './content.mjs';
import { esc } from '../../modules/shared/primitives.mjs';

function localFile(root, file, extensions) {
  if (typeof file !== 'string' || path.isAbsolute(file) || !extensions.includes(path.extname(file).toLowerCase())) {
    throw new ContentError('template asset or instructions must name a supported relative local file');
  }
  let resolved;
  try { resolved = realpathSync(path.resolve(root, file)); } catch { throw new ContentError(`template file does not exist: ${file}`); }
  if (!resolved.startsWith(realpathSync(root) + path.sep)) throw new ContentError('template file must stay inside its template directory');
  return resolved;
}

function assetFile(root, file) {
  return typeof file === 'string' && file.startsWith('brand:')
    ? localFile(BRANDING, file.slice(6), ['.png','.jpg','.jpeg','.webp','.svg'])
    : localFile(root, file, ['.png','.jpg','.jpeg','.webp','.svg']);
}

export function loadTemplateOptions(manifest, root) {
  const result = { ...manifest, templateRoot: root };
  if (manifest.instructions !== undefined) {
    result.instructionsText = readFileSync(localFile(root, manifest.instructions, ['.md']), 'utf8');
    if (!result.instructionsText.trim()) throw new ContentError('template instructions must not be empty');
  }
  const questions = manifest.template_questions ?? [];
  if (!Array.isArray(questions)) throw new ContentError('template_questions must be a list');
  const ids = new Set();
  for (const q of questions) {
    if (!q || typeof q.id !== 'string' || !q.id.startsWith(`${manifest.name}.`) || ids.has(q.id)
      || typeof q.prompt !== 'string' || !q.prompt || !['required','optional'].includes(q.tier) || q.answer_type !== 'decision') {
      throw new ContentError('template question needs a unique template-prefixed id, prompt, tier, and decision answer_type');
    }
    ids.add(q.id);
    if (!Array.isArray(q.choices) || q.choices.length < 2) throw new ContentError(`${q.id}: provide at least two choices`);
    const values = new Set();
    for (const choice of q.choices) {
      if (!choice || typeof choice.value !== 'string' || !/^[a-z0-9-]+$/.test(choice.value) || values.has(choice.value) || typeof choice.label !== 'string' || !choice.label) throw new ContentError(`${q.id}: choices need unique values and labels`);
      values.add(choice.value);
      assetFile(root, choice.image);
    }
  }
  if (manifest.cover_background_question && !ids.has(manifest.cover_background_question)) throw new ContentError('cover_background_question must reference a template question');
  if (manifest.illustrations !== undefined && !Array.isArray(manifest.illustrations)) throw new ContentError('illustrations must be a list');
  const targets = new Set();
  for (const illustration of manifest.illustrations ?? []) {
    const entry = manifest.modules.find(m => (typeof m === 'string' ? m : m.id) === illustration.module);
    const key = `${illustration.module}:${illustration.view}`;
    if (!entry || !illustration.view || targets.has(key)) throw new ContentError('illustration needs a unique selected module/view target');
    if (entry.output && !entry.output.some(v => v.id === illustration.view)) throw new ContentError('illustration view is not selected');
    targets.add(key);
    assetFile(root, illustration.image);
  }
  return result;
}

export function templateQuestions(archetype) {
  return (archetype.template_questions ?? []).map(q => ({ ...q, module_id: archetype.name, module_title: `${archetype.title} preferences` }));
}

export function copyTemplateOptions(archetype, intake, outDir) {
  const copied = new Map();
  const copy = (file) => {
    if (!copied.has(file)) {
      const target = `assets/template/asset-${copied.size + 1}${path.extname(file)}`;
      mkdirSync(path.join(outDir,'assets/template'), { recursive:true });
      copyFileSync(assetFile(archetype.templateRoot,file),path.join(outDir,target));
      copied.set(file,target);
    }
    return copied.get(file);
  };
  const questions = templateQuestions(archetype);
  const galleries = questions.map(q => `<section><h2>${esc(q.prompt)}</h2><div class="choices">${q.choices.map(c => `<figure><img src="${copy(c.image)}" alt="${esc(c.label)}"><figcaption><strong>${esc(c.label)}</strong><p>Choice: ${esc(c.value)}</p></figcaption></figure>`).join('')}</div></section>`).join('');
  if (galleries) writeFileSync(path.join(outDir,'template-choices.html'), `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(archetype.title)} choices</title><style>@font-face{font-family:"Slalom Sans";src:url('fonts/slalom-sans-regular.woff2')}body{font-family:"Slalom Sans",Arial,sans-serif;font-synthesis:none;margin:40px;color:#002FAF}.choices{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}figure{margin:0}img{width:100%;aspect-ratio:16/9;object-fit:cover}p{line-height:1.5}@media(max-width:700px){.choices{grid-template-columns:1fr}}</style><h1>${esc(archetype.title)} preferences</h1><p>Tell your assistant which image to use at the top of the microsite. Your choice will be saved with the intake.</p>${galleries}</html>`);
  const question = questions.find(q => q.id === archetype.cover_background_question);
  const answer = intake?.answers.find(a => a.id === question?.id);
  const selected = answer?.status === 'answered' ? question?.choices.find(c => c.value === answer.answer) : null;
  return {
    coverBackground: selected ? copy(selected.image) : null,
    illustrations: new Map((archetype.illustrations ?? []).map(i => [`${i.module}:${i.view}`, copy(i.image)])),
  };
}
