#!/usr/bin/env python3
"""Copy the weekly status starters and their local assets into a new directory."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from outline import load as load_outline
from sources import package as package_sources

TYPE = Path(__file__).resolve().parents[1]
SKILL = TYPE.parents[1]
UTILITY = SKILL.parent / 'utilities-ui-generation'
PACK = UTILITY / 'branding/packs/slalom/assets'


def validate(report):
    if not isinstance(report, dict):
        raise ValueError('Report must be an object')
    for key in ('project', 'period', 'health', 'summary'):
        if not isinstance(report.get(key), str) or not report[key].strip():
            raise ValueError(f'{key} must be a nonempty string')
    if type(report.get('sample')) is not bool:
        raise ValueError('sample must be a boolean')
    if type(report.get('useIconography')) is not bool:
        raise ValueError('useIconography must be a boolean')
    palette = {'Cyan': '#1BE1F2', 'Coral Red': '#FF4D5F',
               'Purple': '#C7B9FF', 'Chartreuse': '#DEFF4D'}
    color = report.get('secondaryColor')
    if not isinstance(color, dict) or palette.get(color.get('name')) != color.get('hex'):
        raise ValueError('secondaryColor must name an approved Slalom secondary color and hex')
    assessment = report.get('healthAssessment', 'not_assessed' if report['health'] == 'Not assessed' else 'reported')
    if assessment not in {'reported', 'reasoned', 'not_assessed'}:
        raise ValueError('healthAssessment must be reported, reasoned, or not_assessed')
    if assessment == 'not_assessed' and report['health'] != 'Not assessed':
        raise ValueError('not_assessed health must use Not assessed')
    if assessment in {'reported', 'reasoned'}:
        for key in ('healthBasis', 'healthSource'):
            if not isinstance(report.get(key), str) or not report[key].strip():
                raise ValueError(f'{key} is required for a reported or reasoned health assessment')
    if not isinstance(report.get('coverageNote'), str) or not report['coverageNote'].strip():
        raise ValueError('coverageNote must be a nonempty string')
    if not isinstance(report.get('summarySources'), list) or not all(isinstance(x, str) and x.strip() for x in report['summarySources']):
        raise ValueError('summarySources must be an array of nonempty source labels')
    groups = {'accomplishments': ('text', 'source'),
              'nextSteps': ('text', 'owner', 'due', 'source'),
              'milestones': ('name', 'date', 'status', 'source'),
              'risks': ('text', 'impact', 'owner', 'action', 'source'),
              'decisions': ('text', 'owner', 'due', 'source')}
    for key, fields in groups.items():
        if key not in report and 'sections' in report:
            continue
        if not isinstance(report.get(key), list):
            raise ValueError(f'{key} must be an array')
        for row in report[key]:
            if not isinstance(row, dict) or any(not isinstance(row.get(f), str) or not row[f].strip() for f in fields):
                raise ValueError(f'{key} items require nonempty strings: {", ".join(fields)}')
            icon = row.get('icon')
            if icon is not None and (not isinstance(icon, str) or not (PACK / 'iconography' / f'{icon}.svg').is_file()):
                raise ValueError(f'{key} uses an unavailable Slalom icon: {icon}')
    if 'sections' in report:
        if not isinstance(report['sections'], list):
            raise ValueError('sections must be an ordered array')
        seen = set()
        for section in report['sections']:
            if not isinstance(section, dict) or not isinstance(section.get('id'), str) or section['id'] in seen:
                raise ValueError('section IDs must be unique strings')
            seen.add(section['id'])
            if not isinstance(section.get('items'), list):
                raise ValueError(f'{section["id"]} needs an items array')
            for item in section['items']:
                if not isinstance(item, dict) or not isinstance(item.get('source'), (str, list)):
                    raise ValueError(f'{section["id"]} items need source labels')
                source = item['source']
                if not (source.strip() if isinstance(source, str) else source and all(isinstance(x, str) and x.strip() for x in source)):
                    raise ValueError(f'{section["id"]} items need nonempty source labels')
                icon = item.get('icon')
                if icon is not None and (not isinstance(icon, str) or not (PACK / 'iconography' / f'{icon}.svg').is_file()):
                    raise ValueError(f'{section["id"]} uses an unavailable Slalom icon: {icon}')
    return report


def normalize(report, outline):
    """Apply the selected outline and convert old report groups to section items."""
    old = {
        'accomplishments': report.get('accomplishments', []),
        'next-steps': report.get('nextSteps', []),
        'milestones': report.get('milestones', []),
        'risks-and-decisions': [dict(item, kind='Risk') for item in report.get('risks', [])]
                               + [dict(item, kind='Decision') for item in report.get('decisions', [])],
    }
    authored = {section['id']: section for section in report.get('sections', [])}
    active = outline['sections']
    if authored and set(authored) != {section['id'] for section in active}:
        raise ValueError('report section IDs must match the active outline')
    report['sections'] = []
    for definition in active:
        section = {key: definition[key] for key in ('id', 'title', 'layout', 'columns', 'label', 'cardLines')}
        section['items'] = authored[section['id']]['items'] if authored else old.get(section['id'], [])
        if section['layout'] == 'ask' and len(section['items']) > 1:
            raise ValueError(f'{section["id"]} asks for one item at most')
        for item in section['items']:
            if section['layout'] == 'timeline' and any(not isinstance(item.get(key), str) or not item[key].strip() for key in ('name', 'date', 'status')):
                raise ValueError(f'{section["id"]} timeline items need name, date, and status')
            if section['layout'] in ('list', 'cards', 'ask') and not any(isinstance(item.get(key), str) and item[key].strip() for key in ('text', 'description')):
                raise ValueError(f'{section["id"]} items need text or description')
            if section['layout'] == 'table' and any(not isinstance(item.get(column), str) or not item[column].strip() for column in section['columns']):
                raise ValueError(f'{section["id"]} table items need each outlined column')
        report['sections'].append(section)
    return report


def prepare(output, report=None, project_root=None, reset_outline=False):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f'Refusing to replace existing output: {output}')
    if report is None:
        sample = (TYPE / 'templates/report.js').read_text(encoding='utf-8')
        report = json.loads(sample.removeprefix('window.weeklyStatus = ').strip().removesuffix(';'))
    validate(report)
    outline = load_outline(project_root, reset_outline)
    report = normalize(dict(report), outline)
    assets = {
        'regular.woff2': PACK / 'fonts/slalom-sans/Webfont Files/SlalomSans-Regular.woff2',
        'bold.woff2': PACK / 'fonts/slalom-sans/Webfont Files/SlalomSans-Bold.woff2',
        'logo.svg': PACK / 'logos/slalom-logo-blue-RGB.svg',
        'illustration.svg': PACK / 'illustrations/computer/computer-skin-tone-medium.svg',
        'illustration-2.svg': PACK / 'illustrations/gesture-11-messenger-bag/gesture-11-messenger-bag-skin-tone-dark.svg',
        'whiteboard.svg': PACK / 'illustrations/whiteboard/whiteboard-skin-tone-dark.svg',
        'pointing.svg': PACK / 'illustrations/gesture-2-pointing/gesture-2-pointing-skin-tone-medium.svg',
        'high-five.svg': PACK / 'illustrations/high-five/high-five-black-medium-fill.svg',
        'telescope.svg': PACK / 'illustrations/telescope/telescope-skin-tone-light.svg',
        'anime.esm.min.js': UTILITY / 'assets/animejs/vendor/anime.esm.min.js',
        'LICENSE.md': UTILITY / 'assets/animejs/vendor/LICENSE.md',
        'fonts-README.md': PACK / 'fonts/README.md',
    }
    for source in assets.values():
        if not source.is_file():
            raise FileNotFoundError(f'Required asset missing: {source}')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.weekly-status-', dir=output.parent) as staging:
        draft = Path(staging) / 'site'
        shutil.copytree(TYPE / 'templates', draft)
        (draft / 'brief.md').unlink()
        (draft / 'assets').mkdir()
        for name, source in assets.items():
            shutil.copy2(source, draft / 'assets' / name)
        if report['useIconography']:
            shutil.copytree(PACK / 'iconography', draft / 'assets' / 'iconography')
        package_sources(report, project_root, draft)
        (draft / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        (draft / 'report.js').write_text('window.weeklyStatus = ' + json.dumps(report, ensure_ascii=True) + ';\n', encoding='utf-8')
        draft.rename(output)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--report', type=Path, help='Report JSON; omitted for a labeled fictional sample')
    parser.add_argument('--project-root', type=Path, help='Initialized project with tracker copies and saved outline')
    parser.add_argument('--reset-outline', action='store_true', help='Use default sections for this run without editing saved outlines')
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding='utf-8')) if args.report else None
        print(prepare(args.output, report, args.project_root, args.reset_outline))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'{exc}\n')
