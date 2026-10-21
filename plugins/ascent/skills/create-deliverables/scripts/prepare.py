#!/usr/bin/env python3
"""Copy the weekly status starters and their local assets into a new directory."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

SKILL = Path(__file__).resolve().parents[1]
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
    groups = {'accomplishments': ('text', 'source'),
              'nextSteps': ('text', 'owner', 'due', 'source'),
              'milestones': ('name', 'date', 'status', 'source'),
              'risks': ('text', 'impact', 'owner', 'action', 'source'),
              'decisions': ('text', 'owner', 'due', 'source')}
    for key, fields in groups.items():
        if not isinstance(report.get(key), list):
            raise ValueError(f'{key} must be an array')
        for row in report[key]:
            if not isinstance(row, dict) or any(not isinstance(row.get(f), str) or not row[f].strip() for f in fields):
                raise ValueError(f'{key} items require nonempty strings: {", ".join(fields)}')
    return report


def prepare(output, report=None):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f'Refusing to replace existing output: {output}')
    if report is not None:
        validate(report)
    assets = {
        'regular.woff2': PACK / 'fonts/slalom-sans/Webfont Files/SlalomSans-Regular.woff2',
        'bold.woff2': PACK / 'fonts/slalom-sans/Webfont Files/SlalomSans-Bold.woff2',
        'logo.svg': PACK / 'logos/slalom-logo-blue-RGB.svg',
        'illustration.svg': PACK / 'illustrations/computer/computer-skin-tone-medium.svg',
        'illustration-2.svg': PACK / 'illustrations/gesture-11-messenger-bag/gesture-11-messenger-bag-skin-tone-dark.svg',
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
        shutil.copytree(SKILL / 'templates/weekly-status', draft)
        (draft / 'brief.md').unlink()
        (draft / 'assets').mkdir()
        for name, source in assets.items():
            shutil.copy2(source, draft / 'assets' / name)
        if report is not None:
            (draft / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            (draft / 'report.js').write_text('window.weeklyStatus = ' + json.dumps(report, ensure_ascii=True) + ';\n', encoding='utf-8')
        draft.rename(output)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--report', type=Path, help='Report JSON; omitted for a labeled fictional sample')
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding='utf-8')) if args.report else None
        print(prepare(args.output, report))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'{exc}\n')
