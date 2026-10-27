#!/usr/bin/env python3
"""Prepare a standalone, evidence-backed editorial kickoff presentation."""
import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

TYPE = Path(__file__).resolve().parents[1]
WEEKLY = TYPE.parent / 'weekly-status'
PACK = TYPE.parents[2] / 'utilities-ui-generation/branding/packs/slalom/assets'
PALETTE = {'Cyan': '#1BE1F2', 'Coral Red': '#FF4D5F', 'Purple': '#C7B9FF', 'Chartreuse': '#DEFF4D'}
PRESETS = {
    'executive': ['opening', 'context', 'outcomes', 'scope', 'approach', 'decisions', 'next'],
    'core': ['opening', 'context', 'outcomes', 'scope', 'people', 'approach', 'milestones', 'decisions', 'rhythm', 'conditions', 'next'],
    'complete': ['opening', 'context', 'outcomes', 'scope', 'people', 'approach', 'milestones', 'deliverables', 'decisions', 'rhythm', 'conditions', 'logistics', 'next'],
}
LAYOUTS = {'opening', 'editorial', 'outcomes', 'boundaries', 'roster', 'journey', 'milestones', 'decision-flow', 'rhythm', 'commitments'}


def required(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a nonempty string')


def validate(report):
    if not isinstance(report, dict):
        raise ValueError('Kickoff must be an object')
    for key in ('project', 'date', 'depth'):
        required(report.get(key), key)
    if report['depth'] not in PRESETS:
        raise ValueError('depth must be executive, core, or complete')
    if type(report.get('sample')) is not bool:
        raise ValueError('sample must be a boolean')
    color = report.get('secondaryColor')
    if not isinstance(color, dict) or not isinstance(color.get('name'), str) or color.get('name') not in PALETTE or PALETTE[color['name']] != color.get('hex'):
        raise ValueError('Choose an approved secondaryColor name and hex')
    sections = report.get('sections')
    if not isinstance(sections, list) or not sections:
        raise ValueError('sections must be a nonempty array')
    seen = set()
    for section in sections:
        if not isinstance(section, dict):
            raise ValueError('Each section must be an object')
        for key in ('id', 'label', 'title', 'layout'):
            required(section.get(key), f'section {key}')
        if section['id'] in seen or section['layout'] not in LAYOUTS:
            raise ValueError('Section IDs must be unique and layouts supported')
        seen.add(section['id'])
        if 'intro' in section:
            required(section['intro'], 'intro')
        if not isinstance(section.get('items'), list) or not section['items']:
            raise ValueError('Each section needs at least one item')
        for item in section['items']:
            if not isinstance(item, dict):
                raise ValueError('Each item must be an object')
            for key in ('title', 'text'):
                required(item.get(key), key)
            if item.get('state') not in ('confirmed', 'unconfirmed'):
                raise ValueError('Item state must be confirmed or unconfirmed')
            sources = item.get('source')
            if not isinstance(sources, list) or not all(isinstance(s, str) and s.strip() for s in sources):
                raise ValueError('source must be an array of nonempty labels')
            if item['state'] == 'confirmed' and not sources:
                raise ValueError('Confirmed items need evidence')
            if section['layout'] == 'milestones':
                required(item.get('date'), 'milestone date (use Date to agree when unknown)')
            for optional in ('detail', 'frequency'):
                if optional in item:
                    required(item[optional], optional)
    if sections[0]['layout'] != 'opening':
        raise ValueError('The first section must use the opening layout')
    return report


def prepare(output, report=None, project_root=None, depth=None):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f'Refusing to replace existing output: {output}')
    if depth is not None and depth not in PRESETS:
        raise ValueError('Unknown depth')
    if report is None:
        report = json.loads((TYPE / 'templates/example.json').read_text())
        report['depth'] = depth or 'core'
        by_id = {section['id']: section for section in report['sections']}
        report['sections'] = [by_id[key] for key in PRESETS[report['depth']]]
    else:
        report = deepcopy(report)
        if depth is not None and report.get('depth') != depth:
            raise ValueError('Authored content depth must match --depth; curate sections before generation')
    validate(report)
    if not report['sample'] and project_root is None:
        raise ValueError('Real project presentations need --project-root for source packaging')
    spec = importlib.util.spec_from_file_location('kickoff_sources', WEEKLY / 'scripts/sources.py')
    sources = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sources)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.kickoff-', dir=output.parent) as temporary:
        draft = Path(temporary) / 'site'
        (draft / 'presentation').mkdir(parents=True)
        (draft / 'assets').mkdir()
        shutil.copy2(TYPE / 'templates/index.html', draft / 'presentation/index.html')
        for name in ('site.js', 'kickoff.css'):
            shutil.copy2(TYPE / 'templates' / name, draft / name)
        shutil.copy2(WEEKLY / 'templates/site.css', draft / 'site.css')
        assets = {'regular.woff2': 'fonts/slalom-sans/Webfont Files/SlalomSans-Regular.woff2',
                  'bold.woff2': 'fonts/slalom-sans/Webfont Files/SlalomSans-Bold.woff2',
                  'fonts-README.md': 'fonts/README.md',
                  'logo.svg': 'logos/slalom-logo-blue-RGB.svg',
                  'telescope.svg': 'illustrations/telescope/telescope-skin-tone-light.svg'}
        for name, path in assets.items():
            shutil.copy2(PACK / path, draft / 'assets' / name)
        sources.package(report, project_root, draft)
        (draft / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        (draft / 'report.js').write_text('window.projectKickoff = ' + json.dumps(report, ensure_ascii=True) + ';\n')
        draft.rename(output)
    return output / 'presentation/index.html'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--project-root', type=Path)
    parser.add_argument('--depth', choices=PRESETS, help='Example depth; authored reports declare their own depth')
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text()) if args.report else None
        print(prepare(args.output, report, args.project_root, args.depth))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'{exc}\n')
