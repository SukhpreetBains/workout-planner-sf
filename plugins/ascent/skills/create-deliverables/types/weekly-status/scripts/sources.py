"""Package cited tracker rows and accepted evidence as portable HTML snapshots."""
import hashlib
import html
from pathlib import Path
import re
from urllib.parse import urlsplit

ROW_ID = re.compile(r'^[A-Z]{2,}-\d+$')
SAFE_TEXT = {'.md', '.txt', '.yaml', '.yml', '.json', '.csv', '.tsv'}


def yaml_reader():
    try:
        import yaml
    except ImportError as error:
        raise ValueError('Project source packaging requires PyYAML. Run preparation with the Ascent shared/scripts/py launcher.') from error
    return yaml.safe_load


def labels(report):
    found = set(report.get('summarySources', []))
    for name in ('healthSource',):
        found.update(part.strip() for part in report.get(name, '').split(';') if part.strip())
    for section in report.get('sections', []):
        for item in section.get('items', []):
            source = item.get('source', [])
            found.update(source if isinstance(source, list) else (part.strip() for part in source.split(';') if part.strip()))
    return found


def load_rows(root, safe_load):
    rows = {}
    for path in sorted((root / 'workspace/.system/tracker-copies').glob('*.yaml')):
        data = safe_load(path.read_text(encoding='utf-8')) or {}
        for row in data.get('rows') or []:
            key = next((key for key in row if key.endswith(' ID')), None)
            if key and row.get(key):
                rows[str(row[key])] = (data.get('category', path.stem), row)
    return rows


def load_evidence(root, safe_load):
    latest = {}
    for path in (root / 'workspace/.system/applied-updates').glob('*.yaml'):
        data = safe_load(path.read_text(encoding='utf-8')) or {}
        row_id = data.get('tracker_id')
        if not row_id or data.get('review_decision') != 'accepted':
            continue
        reviewed = str(data.get('reviewed_at') or '')
        evidence = [item for update in data.get('updates') or [] for item in update.get('evidence') or [] if isinstance(item, dict) and item.get('excerpt')]
        if row_id not in latest or reviewed > latest[row_id][0]:
            latest[row_id] = (reviewed, evidence)
    return {key: value[1] for key, value in latest.items()}


def snapshot(root, output, ref):
    if not isinstance(ref, str) or not ref.startswith('workspace/'):
        return None
    relative = Path(ref)
    if '..' in relative.parts or relative.is_absolute():
        return None
    target = (root / relative).resolve()
    workspace = (root / 'workspace').resolve()
    if not target.is_relative_to(workspace) or not target.is_file():
        return None
    if target.suffix.lower() not in SAFE_TEXT:
        sibling = target.with_suffix('.md')
        if not sibling.is_file() or not sibling.resolve().is_relative_to(workspace):
            return None
        target = sibling
    if target.stat().st_size > 262144:
        return None
    name = hashlib.sha256(str(target.relative_to(root)).encode()).hexdigest()[:16] + '.html'
    page = output / 'sources' / name
    body = html.escape(target.read_text(encoding='utf-8'))
    page.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Source snapshot</title><style>body{font:16px/1.5 Arial,sans-serif;max-width:75ch;margin:2rem auto;padding:0 1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Source snapshot</h1><p>' + html.escape(str(target.relative_to(root))) + '</p><pre>' + body + '</pre></html>', encoding='utf-8')
    return '../sources/' + name


def package(report, root, output):
    cited = labels(report)
    links = report.get('sourceLinks') or {}
    if not isinstance(links, dict):
        raise ValueError('sourceLinks must be an object')
    for label, url in links.items():
        remote = isinstance(url, str) and url.startswith('https://') and bool(urlsplit(url).hostname) and not any(character.isspace() or ord(character) < 32 for character in url)
        local = isinstance(url, str) and re.fullmatch(r'\.\./sources/[A-Za-z0-9_.-]+\.html', url)
        if not isinstance(label, str) or not (remote or local):
            raise ValueError(f'unsafe source link: {label}')
        if root is None and url.startswith('../sources/'):
            raise ValueError(f'local source link needs a packaged snapshot: {label}')
    if root is None:
        unknown = [label for label in cited if ROW_ID.fullmatch(label)]
        if unknown:
            raise ValueError('tracker IDs need a project root: ' + ', '.join(sorted(unknown)))
        report['sourceDetails'] = {}
        return
    root = Path(root).resolve()
    safe_load = yaml_reader()
    rows = load_rows(root, safe_load)
    unknown = sorted(label for label in cited if ROW_ID.fullmatch(label) and label not in rows)
    if unknown:
        raise ValueError('unknown tracker IDs: ' + ', '.join(unknown))
    evidence = load_evidence(root, safe_load)
    (output / 'sources').mkdir(exist_ok=True)
    details = {}
    for label in sorted(cited):
        if label not in rows:
            if label.startswith('workspace/'):
                link = snapshot(root, output, label)
                details[label] = {'documents': [{'sourceRef': label, 'link': link}], 'evidence': [], 'facts': {}, 'name': label, 'description': ''}
            continue
        category, row = rows[label]
        facts = {key: str(value) for key, value in row.items() if value is not None and key not in ('Description', 'Source Refs') and not key.startswith('_')}
        excerpts = []
        for item in evidence.get(label, []):
            ref = str(item.get('source_ref') or '')
            excerpts.append({'excerpt': str(item['excerpt']), 'sourceRef': ref, 'link': snapshot(root, output, ref)})
        refs = []
        for ref in str(row.get('Source Refs') or '').split(';'):
            if ref.strip():
                refs.append({'sourceRef': ref.strip(), 'link': snapshot(root, output, ref.strip())})
        details[label] = {'category': category, 'name': str(row.get('Name') or label), 'description': str(row.get('Description') or ''), 'facts': facts, 'evidence': excerpts, 'documents': refs}
    for label, url in links.items():
        if url.startswith('../sources/') and not (output / 'sources' / Path(url).name).is_file():
            raise ValueError(f'local source link is missing: {label}')
    report['sourceDetails'] = details
