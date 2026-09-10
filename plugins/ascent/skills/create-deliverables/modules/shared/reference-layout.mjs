import { esc } from './primitives.mjs';

/** Fill a module-owned composition with escaped, template-owned copy. */
export function referenceLayout(template, content) {
  const values = new Map(content.copy.map(({ key, text }) => [key, text]));
  const keys = new Set([...template.matchAll(/\{\{([a-z0-9-]+)\}\}/g)].map((match) => match[1]));
  if (values.size !== content.copy.length) throw new Error('Microsite copy contains duplicate keys');
  for (const key of keys) {
    if (!values.has(key)) throw new Error(`Microsite copy is missing ${key}`);
  }
  for (const key of values.keys()) {
    if (!keys.has(key)) throw new Error(`Microsite copy has unknown key ${key}`);
  }
  // Namespace trusted markup before inserting copy. Author text is never rewritten.
  const isolated = template
    .replace(/class="([^"]+)"/g, (_, classes) => `class="${classes.split(/\s+/).map((name) => `ref-${name}`).join(' ')}"`)
    .replace(/style="([^"]+)"/g, (_, style) => `style="${style.replace(/--([a-zA-Z][\w-]*)/g, '--ref-$1')}"`)
    .replace(/class="ref-ring" data-value="(\d+)"/g, (_, value) => `class="ref-ring" data-value="${value}" style="--ref-ring:${Math.min(Number(value), 100) * 3.6}deg"`)
    .replace(/class="ref-classification"/g, 'class="ref-classification classification"');
  const markup = isolated.replace(/\{\{([a-z0-9-]+)\}\}/g, (_, key) => esc(values.get(key)));
  const cover = content.client && content.date ? ' cover' : '';
  return `<div class="reference-kickoff${cover}">${markup}</div>`;
}
