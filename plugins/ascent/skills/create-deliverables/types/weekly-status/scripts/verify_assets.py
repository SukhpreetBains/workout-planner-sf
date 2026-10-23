#!/usr/bin/env python3
"""Check packaged weekly-status assets before browser review."""

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys


EXTENSIONS = ('.svg', '.png', '.jpg', '.jpeg', '.webp', '.woff2', '.js', '.css')


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for key in ('src', 'href'):
            value = values.get(key, '')
            if value and not value.startswith(('http:', 'https:', '#', 'data:', 'mailto:')):
                self.paths.append(value.split('#', 1)[0].split('?', 1)[0])


def verify(root):
    root = Path(root).resolve()
    report = json.loads((root / 'report.json').read_text(encoding='utf-8'))
    errors = []
    pages = [root / name / 'index.html' for name in ('business', 'expressive', 'animated')]
    if any(not page.is_file() for page in pages):
        errors.append('business, expressive, and animated index.html files are required')

    assets = root / 'assets'
    icon_dir = assets / 'iconography'
    if report.get('useIconography'):
        approved = Path(__file__).resolve().parents[4] / 'utilities-ui-generation/branding/packs/slalom/assets/iconography'
        expected = {path.name for path in approved.glob('*.svg')}
        actual = {path.name for path in icon_dir.glob('*.svg')}
        if actual != expected:
            errors.append(f'approved icon package mismatch: missing {sorted(expected - actual)}, extra {sorted(actual - expected)}')

    for page in pages + [root / 'index.html']:
        if not page.is_file():
            continue
        parser = References()
        source = page.read_text(encoding='utf-8')
        parser.feed(source)
        for path in parser.paths:
            if not (page.parent / path).is_file():
                errors.append(f'{page.relative_to(root)}: missing {path}')

    for path in root.rglob('*'):
        if path.suffix not in {'.css', '.js', '.html'} or path.name == 'report.js':
            continue
        source = path.read_text(encoding='utf-8')
        for match in re.findall(r'url\([\'\"]?([^\)\'\"]+)', source):
            if match.startswith(('data:', 'http:', 'https:')):
                continue
            if not (path.parent / match).is_file():
                errors.append(f'{path.relative_to(root)}: missing CSS asset {match}')
        for name in re.findall(r'[\'\"]([A-Za-z0-9_-]+\.(?:svg|png|jpg|jpeg|webp))[\'\"]', source):
            if not any(assets.rglob(name)):
                errors.append(f'{path.relative_to(root)}: missing referenced image {name}')

    if report.get('useIconography'):
        for group in ('accomplishments', 'nextSteps', 'milestones', 'risks', 'decisions'):
            for item in report.get(group, []):
                if item.get('icon') and not (icon_dir / f"{item['icon']}.svg").is_file():
                    errors.append(f'{group}: missing icon {item["icon"]}.svg')

    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        raise ValueError(f'{len(errors)} asset check(s) failed')
    print(f'Asset check passed: {len(pages)} variants, {len(list(icon_dir.glob("*.svg")))} packaged icons')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        verify(args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f'{exc}\n')
