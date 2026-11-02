"""Load the RAID log vocabulary: tabs, fields, and picklists."""
from pathlib import Path

TYPE = Path(__file__).resolve().parents[1]
SCHEMA = TYPE.parents[3] / 'shared/schema/trackers.yaml'


def yaml_reader():
    try:
        import yaml
    except ImportError as error:
        raise ValueError('RAID log preparation requires PyYAML. Run it with the Ascent shared/scripts/py launcher.') from error
    return yaml.safe_load


def load(root=TYPE):
    """Combine tabs.yaml and one picklist file per field into one lookup."""
    read = lambda path: yaml_reader()(path.read_text(encoding='utf-8'))
    root = Path(root)
    levels = {path.stem: read(path) for path in sorted((root / 'picklists').glob('*.yaml')) if path.stem != 'status'}
    status = read(root / 'picklists/status.yaml')
    layout = read(root / 'tabs.yaml')
    for level in levels.values():
        if 'tracker_column' in level:
            from_schema(level, layout['tabs'])
    return {'tabs': layout['tabs'],
            'fields': layout['fields'],
            'columns': layout['columns'],
            'status': status['status'],
            'tones': status['tones'],
            'levels': levels}


def from_schema(level, tabs, schema_path=SCHEMA):
    """Fill a picklist kept in a tracker column: its values, and how each category's rows map to them."""
    categories = tracker_schema(schema_path)['categories']
    column = level['tracker_column']
    raid = [c for tab in tabs for c in tab['categories']]
    found = next(col for c in raid for col in categories[c]['columns'] if col['name'] == column)
    labels = found['enum_labels']
    level['values'] = [{'value': labels[key], 'definition': found['enum_definitions'][key], 'aliases': [key]}
                       for key in found['enum']]
    level['from_tracker'] = {c: {'column': column, 'map': labels} for c in raid
                             if any(col['name'] == column for col in categories[c]['columns'])}


def tracker_schema(schema_path=SCHEMA):
    return yaml_reader()(Path(schema_path).read_text(encoding='utf-8'))


def tracker_statuses(schema_path=SCHEMA):
    """Status enum for each tracker category, from the shared tracker schema."""
    found = {}
    for category, definition in tracker_schema(schema_path)['categories'].items():
        column = next((c for c in definition['columns'] if c['name'] == 'Status'), None)
        if column and column.get('enum'):
            found[category] = list(column['enum'])
    return found


def tab_for(picklists, category):
    return next(tab for tab in picklists['tabs'] if category in tab['categories'])


def fields_for(picklists, tab_id):
    """Fields an item on this tab carries, in display order."""
    shown = []
    for field in picklists['fields']:
        if 'picklist' in field:
            applies = tab_id in picklists['levels'][field['picklist']]['tabs']
        elif 'only' in field:
            applies = tab_id in field['only']
        else:
            applies = tab_id not in field.get('except', [])
        if applies:
            shown.append(field)
    return shown


def is_open(picklists, category, status):
    groups = picklists['status'][category]
    if status in groups['open']:
        return True
    if status in groups['closed']:
        return False
    raise ValueError(f'{category} status is not in the tracker schema: {status}')


def tone(picklists, category, status):
    """Status dot tone for a tracker status."""
    found = picklists['status'][category]['tone'].get(status)
    if found is None:
        raise ValueError(f'{category} status has no tone: {status}')
    return found


def level_value(picklists, level, value):
    """Return the canonical level for a value or source wording, or raise."""
    definition = picklists['levels'][level]
    text = str(value).strip().lower()
    for entry in definition['values']:
        if text == entry['value'].lower() or text in entry['aliases']:
            return entry['value']
    allowed = ', '.join(entry['value'] for entry in definition['values'])
    raise ValueError(f'{definition["label"]} must be one of {allowed}: {value}')


def from_tracker(picklists, level, category, row):
    """Map a recorded tracker value to a level, when this level has one for the category."""
    rule = picklists['levels'][level].get('from_tracker', {}).get(category)
    if not rule:
        return None
    return rule['map'].get(row.get(rule['column']))
