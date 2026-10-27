import { rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const skill = new URL('../node_modules/dom-to-pptx/skills/dom-to-pptx-skill/', import.meta.url);
rmSync(fileURLToPath(skill), { recursive: true, force: true });
