#!/usr/bin/env python3
"""Validate a RAID log against the picklists and package it as a standalone site."""
import argparse
from copy import deepcopy
from datetime import date
import importlib.util
import json
import re
from pathlib import Path
import shutil
import tempfile
from collect import collect, records
from export import workbook_name, write_workbook
from picklists import TYPE, fields_for, is_open, level_value, load, tone, tracker_schema, tracker_statuses

WEEKLY = TYPE.parent / 'weekly-status'
PACK = TYPE.parents[2] / 'utilities-ui-generation/branding/packs/slalom/assets'
PALETTE = {'Cyan': '#1BE1F2', 'Coral Red': '#FF4D5F', 'Purple': '#C7B9FF', 'Chartreuse': '#DEFF4D'}
ASSETS = {'regular.woff2': 'fonts/slalom-sans/Webfont Files/SlalomSans-Regular.woff2',
          'bold.woff2': 'fonts/slalom-sans/Webfont Files/SlalomSans-Bold.woff2',
          'fonts-README.md': 'fonts/README.md',
          'logo.svg': 'logos/slalom-logo-blue-RGB.svg'}


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a nonempty string')
    return value


def labels(value, name):
    if not isinstance(value, list) or not value or not all(isinstance(x, str) and x.strip() for x in value):
        raise ValueError(f'{name} must be a nonempty array of labels')
    return value


def iso_date(value, name):
    try:
        date.fromisoformat(text(value, name))
    except ValueError as error:
        raise ValueError(f'{name} must be a YYYY-MM-DD date') from error


def validate_field(field, value, where, picklists):
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValueError(f'{where}: {field["key"]} must be null or an object')
    text(value.get('value'), f'{where}: {field["key"]} value')
    basis = value.get('basis')
    if basis not in field['bases']:
        raise ValueError(f'{where}: {field["key"]} basis must be one of {", ".join(field["bases"])}')
    if basis == 'recorded':
        labels(value.get('from'), f'{where}: {field["key"]} from')
    else:
        labels(value.get('source'), f'{where}: {field["key"]} source')
    if basis == 'assessed':
        text(value.get('reason'), f'{where}: {field["key"]} reason')
    if field.get('type') == 'date':
        iso_date(value['value'], f'{where}: {field["key"]}')
    if 'picklist' in field and level_value(picklists, field['picklist'], value['value']) != value['value']:
        raise ValueError(f'{where}: {field["key"]} must use the canonical picklist value, not {value["value"]}')


def validate(log, picklists=None, statuses=None):
    picklists = picklists or load()
    statuses = statuses or tracker_statuses()
    if not isinstance(log, dict):
        raise ValueError('RAID log must be an object')
    text(log.get('project'), 'project')
    iso_date(log.get('asOf'), 'asOf')
    if type(log.get('sample')) is not bool:
        raise ValueError('sample must be a boolean')
    color = log.get('secondaryColor')
    if not isinstance(color, dict) or PALETTE.get(color.get('name')) != color.get('hex'):
        raise ValueError('secondaryColor must name an approved Slalom secondary color and hex')
    text(log.get('coverageNote'), 'coverageNote')
    omitted = log.get('omitted', [])
    if not isinstance(omitted, list) or not all(isinstance(o, dict) and text(o.get('key'), 'omitted key') and text(o.get('reason'), 'omitted reason') for o in omitted):
        raise ValueError('omitted must be an array of {key, reason}')
    items = log.get('items')
    if not isinstance(items, list):
        raise ValueError('items must be an array')
    tabs = {tab['id']: tab for tab in picklists['tabs']}
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Each item must be an object')
        key = text(item.get('key'), 'item key')
        where = item.get('id') or key
        if key in seen:
            raise ValueError(f'Duplicate item key: {key}')
        seen.add(key)
        tab = tabs.get(item.get('tab'))
        if not tab or item.get('category') not in tab['categories']:
            raise ValueError(f'{where}: category must belong to its tab')
        if item.get('id') != key:
            raise ValueError(f'{where}: id must be the tracker ID, the same as key; the log holds approved items only')
        for name in ('title', 'description'):
            text(item.get(name), f'{where}: {name}')
        if item.get('status') not in statuses[item['category']]:
            raise ValueError(f'{where}: status must be a {item["category"]} tracker status')
        labels(item.get('source'), f'{where}: source')
        allowed = {f['key'] for f in fields_for(picklists, tab['id'])}
        extra = set(item) - allowed - {'key', 'id', 'category', 'tab', 'title', 'description', 'status', 'source', 'pendingChanges'}
        if extra:
            raise ValueError(f'{where}: fields not used on {tab["label"]}: {", ".join(sorted(extra))}')
        for field in fields_for(picklists, tab['id']):
            validate_field(field, item.get(field['key']), where, picklists)
        priority = item.get('priority')
        open_item = is_open(picklists, item['category'], item['status'])
        if priority and priority['basis'] == 'assessed':
            if not open_item:
                raise ValueError(f'{where}: assess priority only for open items')
            target = item.get('target')
            if target and target['value'] < log['asOf'] and priority['value'] != 'High':
                raise ValueError(f'{where}: open past its target date {target["value"]}, so assessed priority must be High')
        reasons = [v['reason'].strip().lower() for v in item.values() if isinstance(v, dict) and v.get('basis') == 'assessed']
        if len(reasons) != len(set(reasons)):
            raise ValueError(f'{where}: give each assessed field its own reason')
    check_links(log, picklists)
    check_reasons(items)
    return log


def check_links(log, picklists):
    """A link field names other items in this log, such as the action a next action points to."""
    tabs = {item['key']: item['tab'] for item in log['items']}
    omitted = {o['key'] for o in log.get('omitted', [])}
    for item in log['items']:
        for field in fields_for(picklists, item['tab']):
            value = item.get(field['key'])
            if not field.get('link') or not value:
                continue
            for key in value['from']:
                if key not in tabs and key not in omitted:
                    raise ValueError(f'{item.get("id") or item["key"]}: {field["key"]} links to {key}, which is not in the log')
                if field['key'] == 'nextAction' and key in tabs and tabs[key] != 'actions':
                    raise ValueError(f'{item.get("id") or item["key"]}: nextAction must link to a tracked action, not {key}')


def check_reasons(items, limit=3):
    """Assessments are judged item by item: reject one template reused across many items."""
    seen = {}
    for item in items:
        for key, value in item.items():
            if not isinstance(value, dict) or value.get('basis') != 'assessed':
                continue
            reason = value['reason'].lower()
            # Remove the item's own words, so pasting its title or description does not disguise a template.
            for own in (item['description'], item['title'], item.get('id') or '', item['key']):
                if own:
                    reason = reason.replace(own.lower(), '')
            reason = re.sub(r'[\W_]+', ' ', reason).strip()
            seen.setdefault((key, reason), []).append(item.get('id') or item['key'])
    for (key, _), ids in seen.items():
        if len(ids) > limit:
            raise ValueError(f'{key}: the same assessment reason is used for {len(ids)} items ({", ".join(ids[:5])}); '
                             'judge each item and cite a fact specific to it')


def check_project(log, root):
    """Every RAID item must appear or be omitted with a reason, and approved values must match the trackers."""
    expected = {item['key']: item for item in collect(root, log['asOf'])['items']}
    present = {item['key'] for item in log['items']}
    omitted = {o['key'] for o in log.get('omitted', [])}
    missing = sorted(set(expected) - present - omitted)
    if missing:
        raise ValueError('RAID items missing without an omitted reason: ' + ', '.join(missing[:10]))
    unknown = sorted(present - set(expected))
    if unknown:
        raise ValueError('Items not found in the approved trackers (review inbox items are never included): '
                         + ', '.join(unknown[:10]))
    for item in log['items']:
        current = expected[item['key']]
        for name in ('category', 'status', 'impactArea'):
            if item.get(name) != current.get(name):
                raise ValueError(f'{item.get("id") or item["key"]}: {name} must match the current tracker row ({current[name]})')


def vocabulary(picklists):
    """What the page needs to render: tabs, fields, colors, and labels."""
    return {'tabs': [{'id': tab['id'], 'label': tab['label'], 'kinds': tab.get('kinds', {}),
                      'fields': [{k: f[k] for k in ('key', 'label', 'type', 'link') if k in f} for f in fields_for(picklists, tab['id'])]}
                     for tab in picklists['tabs']],
            'columns': picklists['columns'],
            'tones': {name: {'color': t['color'], 'hollow': bool(t.get('hollow')), 'label': t['label']} for name, t in picklists['tones'].items()},
            'levels': {name: {v['value']: {'color': v['color'], 'squares': v.get('squares', 1)} for v in level['values']}
                       for name, level in picklists['levels'].items() if all('color' in v for v in level['values'])}}


def enrich(log, picklists):
    for item in log['items']:
        item['open'] = is_open(picklists, item['category'], item['status'])
        item['tone'] = tone(picklists, item['category'], item['status'])
        item['citations'] = list(dict.fromkeys(item['source'] + [label for field in fields_for(picklists, item['tab'])
                                                                 for value in [item.get(field['key'])] if value
                                                                 for label in value.get('from', []) + value.get('source', [])]))
    log['items'].sort(key=lambda item: attention_order(item, log['asOf']))
    log['vocabulary'] = vocabulary(picklists)
    return log


def attention_order(item, as_of):
    """Open before closed; overdue first, most overdue on top; then oldest raised first."""
    target = (item.get('target') or {}).get('value')
    raised = (item.get('dateRaised') or {}).get('value')
    overdue = bool(item['open'] and target and target < as_of)
    return (not item['open'], not overdue, target if overdue else '', raised is None, raised or '', item.get('id') or '~' + item['key'])


def weekly_sources():
    spec = importlib.util.spec_from_file_location('raid_sources', WEEKLY / 'scripts/sources.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def package_sources(log, root, output):
    """Source details for every citation: tracker rows and documents."""
    cited = {label for item in log['items'] for label in item['citations']}
    if root is None:
        log['sourceDetails'] = {}
        return
    sources = weekly_sources()
    root = Path(root).resolve()
    found, _ = records(root, tracker_schema())
    evidence = sources.load_evidence(root, sources.yaml_reader())
    (output / 'sources').mkdir(exist_ok=True)
    def document(ref):
        # Snapshot links are written for pages one folder down; this page sits at the output root.
        link = sources.snapshot(root, output, ref)
        return {'sourceRef': ref, 'link': link.removeprefix('../') if link else None}
    details = {}
    for label in sorted(cited):
        if label.startswith('workspace/'):
            details[label] = {'name': label, 'documents': [document(label)], 'evidence': [], 'facts': {}}
            continue
        if label not in found:
            raise ValueError(f'Unknown source label: {label}')
        record = found[label]
        fields = record['fields']
        refs = [r.strip() for r in str(fields.get('Source Refs') or '').split(';') if r.strip()]
        details[label] = {
            'name': str(fields.get('Name') or label), 'category': record['category'],
            'description': str(fields.get('Description') or ''),
            'facts': {k: str(v) for k, v in fields.items() if v not in (None, '') and k not in ('Name', 'Description', 'Source Refs', 'Relationships', 'Notes')},
            'evidence': [{'excerpt': str(e.get('excerpt')), **document(str(e.get('source_ref') or ''))} for e in evidence.get(label, []) if isinstance(e, dict) and e.get('excerpt')],
            'documents': [document(str(ref)) for ref in refs]}
    log['sourceDetails'] = details


def prepare(output, log=None, project_root=None):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f'Refusing to replace existing output: {output}')
    picklists = load()
    log = deepcopy(log) if log is not None else json.loads((TYPE / 'templates/example.json').read_text(encoding='utf-8'))
    validate(log, picklists)
    if not log['sample'] and project_root is None:
        raise ValueError('A project RAID log needs --project-root for coverage checks and source packaging')
    if project_root is not None:
        check_project(log, project_root)
    enrich(log, picklists)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.raid-log-', dir=output.parent) as temporary:
        draft = Path(temporary) / 'site'
        (draft / 'assets').mkdir(parents=True)
        for name in ('index.html', 'raid.css', 'raid.js'):
            shutil.copy2(TYPE / 'templates' / name, draft / name)
        for name, path in ASSETS.items():
            shutil.copy2(PACK / path, draft / 'assets' / name)
        package_sources(log, project_root, draft)
        log['exportFile'] = workbook_name(log)
        write_workbook(log, picklists, tracker_schema(), draft / log['exportFile'])
        (draft / 'raid.json').write_text(json.dumps(log, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        (draft / 'report.js').write_text('window.raidLog = ' + json.dumps(log, ensure_ascii=True) + ';\n', encoding='utf-8')
        draft.rename(output)
    return output / 'index.html'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--log', type=Path, help='Completed raid.json; omitted for a labeled fictional sample')
    parser.add_argument('--project-root', type=Path)
    args = parser.parse_args()
    try:
        log = json.loads(args.log.read_text(encoding='utf-8')) if args.log else None
        print(prepare(args.output, log, args.project_root))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'{exc}\n')
