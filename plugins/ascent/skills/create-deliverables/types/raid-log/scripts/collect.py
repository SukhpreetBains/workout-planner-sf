#!/usr/bin/env python3
"""Build a starter RAID log from approved tracker rows.

Every approved RAID item in the project is included, with the values the
trackers and their links already record. Review inbox proposals are not
approved, so they never appear in the log. The agent then fills remaining fields from the
cited sources before running prepare.py.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import re
from picklists import fields_for, from_tracker, load, tab_for, tracker_schema, yaml_reader

LIVE_REVIEW = {'pending', 'flagged'}
OWNER_LINK = {'decision': 'decided_by'}
DATE_TARGETS = {'milestone', 'deliverable'}
PLAN_SOURCES = {'action_item', 'proposal'}
# The standard accent; readers can switch it with the page's Color button.
DEFAULT_COLOR = {'name': 'Coral Red', 'hex': '#FF4D5F'}


def iso(value):
    """Tracker copies store dates as text such as '2026-10-02 00:00:00'."""
    match = re.match(r'\d{4}-\d{2}-\d{2}', str(value or '').strip())
    return match.group(0) if match else None


def links(value):
    found = []
    for part in str(value or '').split(';'):
        meaning, _, target = part.partition(':')
        if target.strip():
            found.append((meaning.strip(), target.strip()))
    return found


def recorded(value, sources):
    return {'value': value, 'basis': 'recorded', 'from': sorted(set(sources))} if value else None


def records(root, schema):
    """Approved tracker rows keyed by tracker ID, and the live proposals that would change each one."""
    read = yaml_reader()
    found = {}
    system = Path(root) / 'workspace/.system'
    for path in sorted((system / 'tracker-copies').glob('*.yaml')):
        data = read(path.read_text(encoding='utf-8')) or {}
        category = data.get('category', path.stem)
        if category not in schema['categories']:
            continue
        for row in data.get('rows') or []:
            key = next((row[k] for k in row if k.endswith(' ID') and row[k]), None)
            if key:
                found[str(key)] = {'category': category, 'fields': row}
    pending_changes = {}
    for path in sorted((system / 'proposed-updates').glob('*.y*ml')):
        for update in (read(path.read_text(encoding='utf-8')) or {}).get('updates') or []:
            if ((update.get('review') or {}).get('state', 'pending') in LIVE_REVIEW
                    and update.get('action') == 'update' and update.get('id')):
                pending_changes.setdefault(str(update['id']), []).append(str(update.get('proposal_id') or ''))
    return found, pending_changes


def collect(root, as_of=None):
    picklists = load()
    schema = tracker_schema()
    found, pending_changes = records(root, schema)
    raid = {c for tab in picklists['tabs'] for c in tab['categories']}

    def name(key):
        record = found.get(key)
        return str(record['fields'].get('Name') or key).strip() if record else None

    incoming = {}
    for key, record in found.items():
        for meaning, target in links(record['fields'].get('Relationships')):
            incoming.setdefault(target, []).append((meaning, key))

    items = []
    for key, record in found.items():
        category = record['category']
        if category not in raid:
            continue
        row = record['fields']
        tab = tab_for(picklists, category)
        own = links(row.get('Relationships'))
        targets = lambda meanings, categories=None: [t for m, t in own if m in meanings and t in found
                                                     and (categories is None or found[t]['category'] in categories)]
        values = {}
        owners = targets({OWNER_LINK.get(category, 'owned_by')})
        values['owner'] = recorded('; '.join(name(t) for t in owners), owners)
        raisers = targets({'raised_by'})
        values['raisedBy'] = recorded('; '.join(name(t) for t in raisers), raisers)
        values['dateRaised'] = recorded(iso(row.get('Date')), [key])
        target = iso(row.get('Target Date'))
        if target:
            values['target'] = recorded(target, [key])
        else:
            dated = sorted((iso(found[t]['fields'].get('Target Date')), t)
                           for t in targets({'impacts', 'blocks', 'depends_on', 'applies_to'}, DATE_TARGETS)
                           if iso(found[t]['fields'].get('Target Date')))
            values['target'] = recorded(dated[0][0], [dated[0][1]]) if dated else None
        values['impactArea'] = recorded(from_tracker(picklists, 'impact-area', category, row), [key])
        values['severity'] = recorded(from_tracker(picklists, 'severity', category, row), [key])
        responders = [s for m, s in incoming.get(key, []) if m == 'addresses' and found[s]['category'] in PLAN_SOURCES]
        open_actions = sorted((iso(found[s]['fields'].get('Target Date')) or '9999', s) for s in responders
                              if found[s]['category'] == 'action_item'
                              and found[s]['fields'].get('Status') in picklists['status']['action_item']['open'])
        values['nextAction'] = recorded(name(open_actions[0][1]), [open_actions[0][1]]) if open_actions else None
        addressed = targets({'addresses'}, raid - {'action_item'})
        values['addresses'] = recorded('; '.join(name(t) for t in addressed), addressed)
        values['outcome'] = recorded(str(row.get('Resolution') or '').strip(), [key])
        values['resolutionPlan'] = recorded('; '.join(name(s) for s in responders), responders)
        item = {'key': key, 'id': key, 'category': category, 'tab': tab['id'],
                'title': str(row.get('Name') or '').strip(), 'description': str(row.get('Description') or '').strip(),
                'status': str(row.get('Status') or '').strip(), 'source': [key]}
        if key in pending_changes:
            item['pendingChanges'] = pending_changes[key]
        for field in fields_for(picklists, tab['id']):
            item[field['key']] = values.get(field['key'])
        items.append(item)
    order = {tab['id']: i for i, tab in enumerate(picklists['tabs'])}
    items.sort(key=lambda i: (order[i['tab']], i['id'], i['title']))
    project = yaml_reader()((Path(root) / 'workspace/.system/project.yaml').read_text(encoding='utf-8')) or {}
    return {'project': str(project.get('project') or project.get('opportunity') or project.get('account') or '').strip(),
            'asOf': as_of or date.today().isoformat(), 'sample': False, 'secondaryColor': DEFAULT_COLOR,
            'coverageNote': '', 'omitted': [], 'items': items}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='Starter raid.json to write')
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--as-of', help='Evidence cutoff date, YYYY-MM-DD; defaults to today')
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError(f'Refusing to replace existing file: {args.output}')
        log = collect(args.project_root, args.as_of)
        args.output.write_text(json.dumps(log, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        counts = {}
        for item in log['items']:
            counts[item['tab']] = counts.get(item['tab'], 0) + 1
        print(json.dumps({'output': str(args.output), 'items': len(log['items']), 'byTab': counts}))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'{exc}\n')
