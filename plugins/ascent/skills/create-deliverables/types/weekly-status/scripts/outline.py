"""Validate and load a reusable weekly status section outline."""
from pathlib import Path
import re

TYPE = Path(__file__).resolve().parents[1]
PLUGIN = TYPE.parents[3]
DEFAULT = TYPE / 'outline.md'
CATEGORIES = set(re.findall(r'^  ([a-z_]+):\s*$', (PLUGIN / 'shared/schema/trackers.yaml').read_text().split('categories:', 1)[1], re.M))
LAYOUTS = {'list', 'cards', 'timeline', 'table', 'ask'}
FIELDS = ('Layout', 'Label', 'Card lines', 'Columns', 'Draws on', 'Contains', 'Leave out')
FIELD_RE = re.compile(r'(?:^|\s)(' + '|'.join(re.escape(x) for x in FIELDS) + r'):\s*')


def slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def parse(markdown):
    result = {'sections': [], 'optional': []}
    area = None
    for line in markdown.splitlines():
        if line.startswith('## '):
            area = {'Sections': 'sections', 'Optional sections': 'optional'}.get(line[3:].strip())
            continue
        match = re.match(r'^\s*(?:\d+\.|-)\s+\*\*(.+?)\.?\*\*\s*(.*)', line)
        if match and area:
            name = match.group(1).rstrip('.').strip()
            result[area].append({'id': slug(name), 'title': name, '_text': match.group(2)})
        elif area and result[area] and line.startswith(' '):
            result[area][-1]['_text'] += ' ' + line.strip()
    for area in result:
        for section in result[area]:
            content = section.pop('_text')
            marks = list(FIELD_RE.finditer(content))
            fields = {}
            for n, mark in enumerate(marks):
                end = marks[n + 1].start() if n + 1 < len(marks) else len(content)
                fields[mark.group(1)] = content[mark.end():end].strip().rstrip('.')
            section.update({
                'layout': (re.match(r'`([a-z]+)`', fields.get('Layout', '')) or [None, ''])[1],
                'categories': re.findall(r'`([a-z_]+)`', fields.get('Draws on', '')),
                'contains': fields.get('Contains', ''),
                'leaveOut': fields.get('Leave out', ''),
                'columns': [x.strip() for x in fields.get('Columns', '').split(',') if x.strip()],
                'label': fields.get('Label', ''),
                'cardLines': [x.strip() for x in fields.get('Card lines', '').split(',') if x.strip()],
            })
    return result


def validate(markdown):
    result = parse(markdown)
    if not result['sections']:
        raise ValueError('outline requires a Sections list')
    seen = set()
    for section in result['sections'] + result['optional']:
        name = section['title']
        if section['id'] in seen:
            raise ValueError(f'duplicate section name: {name}')
        seen.add(section['id'])
        if len(name.split()) > 5:
            raise ValueError(f'section name is too long: {name}')
        if section['layout'] not in LAYOUTS:
            raise ValueError(f'unsupported layout in {name}: {section["layout"]}')
        if not section['categories'] or set(section['categories']) - CATEGORIES:
            raise ValueError(f'invalid tracker categories in {name}')
        if len(section['contains'].split()) < 4 or len(section['leaveOut'].split()) < 3:
            raise ValueError(f'{name} needs Contains and Leave out guidance')
        if section['layout'] == 'table' and len(section['columns']) < 2:
            raise ValueError(f'{name} needs at least two table columns')
        if section['layout'] == 'cards' and not section['label']:
            raise ValueError(f'{name} needs a card label')
        if section['cardLines'] and section['layout'] != 'cards':
            raise ValueError(f'{name} uses Card lines outside cards')
    return result


def load(project_root=None, reset=False):
    if reset or project_root is None:
        return validate(DEFAULT.read_text(encoding='utf-8'))
    base = Path(project_root) / 'workspace/.system/outlines'
    for name in ('weekly-status.md', 'weekly-status-outlined.md'):
        path = base / name
        if path.is_file():
            return validate(path.read_text(encoding='utf-8'))
    return validate(DEFAULT.read_text(encoding='utf-8'))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('outline', type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.outline.read_text(encoding='utf-8'))
        print(f'Outline valid: {len(result["sections"])} sections, {len(result["optional"])} optional')
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
