"""Section customization and portable evidence checks for weekly status."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import yaml

TYPE_SCRIPTS = Path(__file__).resolve().parents[1] / 'types/weekly-status/scripts'
sys.path.insert(0, str(TYPE_SCRIPTS))
from outline import DEFAULT, load, validate as validate_outline
from prepare import prepare


class CombinedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.report = json.loads((DEFAULT.parent / 'templates/report.js').read_text().removeprefix('window.weeklyStatus = ').strip().removesuffix(';'))
        self.outlines = self.root / 'workspace/.system/outlines'
        self.outlines.mkdir(parents=True)

    def test_saved_outline_order_and_reset(self):
        original = DEFAULT.read_text()
        entries = original.split('## Sections\n\n', 1)[1].split('\n## Optional sections', 1)[0].splitlines()
        custom = original.split('## Sections\n\n', 1)[0] + '## Sections\n\n' + entries[2] + '\n' + entries[0] + '\n\n## Optional sections\n\n' + original.split('## Optional sections\n\n', 1)[1]
        (self.outlines / 'weekly-status-outlined.md').write_text(custom)
        self.assertEqual([item['id'] for item in load(self.root)['sections']], ['milestones', 'accomplishments'])
        (self.outlines / 'weekly-status.md').write_text(original)
        self.assertEqual(len(load(self.root)['sections']), 4)
        self.assertEqual(len(load(self.root, reset=True)['sections']), 4)
        (self.outlines / 'weekly-status.md').unlink()
        out = prepare(self.root / 'v1', self.report, self.root, template='business')
        self.assertEqual([item['id'] for item in json.loads((out / 'report.json').read_text())['sections']], ['milestones', 'accomplishments'])
        self.assertTrue((self.outlines / 'weekly-status-outlined.md').is_file())

    def test_invalid_outline_fields(self):
        text = DEFAULT.read_text()
        for replacement in ('Layout: `grid`', 'Draws on: `imaginary`', 'Contains: vague', 'Leave out: no'):
            changed = text.replace('Layout: `list`', replacement, 1) if 'Layout:' in replacement else text.replace('Draws on: `decision`, `action_item`, `milestone`, `deliverable`, `session`', replacement, 1) if 'Draws on:' in replacement else text.replace('Contains: material progress during this reporting period', replacement, 1) if 'Contains:' in replacement else text.replace('Leave out: planned or unverified completion', replacement, 1)
            with self.assertRaises(ValueError):
                validate_outline(changed)
        with self.assertRaises(ValueError):
            validate_outline(text.replace('2. **Next steps.**', '2. **Accomplishments.**'))
        with self.assertRaises(ValueError):
            validate_outline(text.replace('Columns: Commitment, Owner, Status, Target', 'Columns: Commitment'))
        with self.assertRaises(ValueError):
            validate_outline(text.replace('Label: workstream name.', ''))

    def test_custom_table_cards_and_reorder(self):
        text = DEFAULT.read_text()
        optional = text.split('## Optional sections\n\n', 1)[1].splitlines()
        sections = [line for line in text.split('## Sections\n\n', 1)[1].split('## Optional sections', 1)[0].splitlines() if line]
        custom = '# Custom\n\n## Sections\n\n' + '\n'.join([optional[1], sections[2], optional[0]]) + '\n\n## Optional sections\n\n'
        # Optional library entries are ordered: Workstreams, Action items.
        custom = '# Custom\n\n## Sections\n\n' + '\n'.join([optional[1], sections[2], optional[0]]) + '\n'
        self.assertEqual([x['id'] for x in validate_outline(custom)['sections']], ['action-items', 'milestones', 'workstreams'])
        (self.outlines / 'weekly-status.md').write_text(custom)
        self.report['sections'] = [
            {'id': 'action-items', 'items': [{'Commitment': 'Schedule review', 'Owner': 'Lead', 'Status': 'Open', 'Target': 'Friday', 'source': 'Fictional sample plan'}]},
            {'id': 'milestones', 'items': self.report['milestones']},
            {'id': 'workstreams', 'items': [{'name': 'Pilot', 'text': 'Review prepared', 'Progress': 'Package ready', 'In the way': 'Access pending', 'source': 'Fictional sample notes'}]},
        ]
        out = prepare(self.root / 'custom', self.report, self.root, template='business')
        data = json.loads((out / 'report.json').read_text())
        self.assertEqual([x['layout'] for x in data['sections']], ['table', 'timeline', 'cards'])
        self.assertEqual([x['id'] for x in data['sections']], ['action-items', 'milestones', 'workstreams'])
        with self.assertRaises(ValueError):
            prepare(self.root / 'bad', dict(self.report, sections=self.report['sections'][:-1]), self.root, template='business')

    def test_current_row_and_historical_excerpt_with_safe_snapshot(self):
        tracker = self.root / 'workspace/.system/tracker-copies'
        tracker.mkdir(parents=True)
        (tracker / 'pain_point.yaml').write_text(yaml.safe_dump({'category': 'pain_point', 'rows': [{'Pain Point ID': 'PAIN-1001', 'Name': '<Current>', 'Status': 'Open', 'Description': 'Current reviewed status', 'Source Refs': 'workspace/notes.md'}]}))
        applied = self.root / 'workspace/.system/applied-updates'
        applied.mkdir()
        (applied / 'one.yaml').write_text(yaml.safe_dump({'tracker_id': 'PAIN-1001', 'review_decision': 'accepted', 'reviewed_at': '2026-10-01', 'updates': [{'evidence': [{'excerpt': '<old> statement', 'source_ref': 'workspace/notes.md'}]}]}))
        (applied / 'two.yaml').write_text(yaml.safe_dump({'tracker_id': 'PAIN-1001', 'review_decision': 'accepted', 'reviewed_at': '2026-10-02', 'updates': [{'evidence': [{'excerpt': '<new> statement', 'source_ref': 'workspace/notes.md'}]}]}))
        (applied / 'three.yaml').write_text(yaml.safe_dump({'tracker_id': 'PAIN-1001', 'review_decision': 'rejected', 'reviewed_at': '2026-10-03', 'updates': [{'evidence': [{'excerpt': 'rejected statement', 'source_ref': 'workspace/notes.md'}]}]}))
        (self.root / 'workspace/notes.md').write_text('A <script>alert(1)</script> source')
        self.report['summarySources'] = ['PAIN-1001', 'workspace/notes.md']
        self.report['accomplishments'][0]['source'] = 'PAIN-1001'
        out = prepare(self.root / 'sourced', self.report, self.root, template='business')
        data = json.loads((out / 'report.json').read_text())
        detail = data['sourceDetails']['PAIN-1001']
        self.assertEqual(detail['facts']['Status'], 'Open')
        self.assertEqual(detail['evidence'][0]['excerpt'], '<new> statement')
        link = detail['evidence'][0]['link']
        self.assertTrue((out / 'sources' / Path(link).name).is_file())
        page = (out / 'sources' / Path(link).name).read_text()
        self.assertIn('&lt;script&gt;', page)
        self.assertNotIn('<script>', page)
        self.assertEqual(data['sourceDetails']['workspace/notes.md']['documents'][0]['link'], link)
        with self.assertRaises(ValueError):
            prepare(self.root / 'unknown', dict(self.report, summarySources=['PAIN-9999']), self.root, template='business')

    def test_missing_documents_and_unsafe_links(self):
        tracker = self.root / 'workspace/.system/tracker-copies'
        tracker.mkdir(parents=True)
        (tracker / 'risk.yaml').write_text(yaml.safe_dump({'category': 'risk', 'rows': [{'Risk ID': 'RISK-1234', 'Name': 'Gap', 'Status': 'Open', 'Source Refs': 'workspace/missing.md; workspace/../secret.md'}]}))
        self.report['summarySources'] = ['RISK-1234']
        out = prepare(self.root / 'missing', self.report, self.root, template='business')
        documents = json.loads((out / 'report.json').read_text())['sourceDetails']['RISK-1234']['documents']
        self.assertTrue(all(item['link'] is None for item in documents))
        with self.assertRaises(ValueError):
            prepare(self.root / 'unsafe', dict(self.report, sourceLinks={'bad': 'javascript:alert(1)'}), self.root, template='business')
        self.assertFalse((self.root / 'unsafe').exists())
        with self.assertRaises(ValueError):
            prepare(self.root / 'broken-local', dict(self.report, sourceLinks={'bad': '../sources/missing.html'}))

    def test_malformed_custom_items_and_multiple_timelines(self):
        base = DEFAULT.read_text()
        extra = '- **Decision timeline.** Layout: `timeline`. Draws on: `decision`. Contains: reviewed dated decisions during the period. Leave out: undecided or undated questions.\n'
        custom = base.replace('## Optional sections', extra + '\n## Optional sections')
        (self.outlines / 'weekly-status.md').write_text(custom)
        self.report['sections'] = [{'id': item['id'], 'items': []} for item in load(self.root)['sections']]
        self.report['sections'][-1]['items'] = [{'name': 'Access choice', 'date': 'Friday', 'status': 'Approved', 'source': 'Fictional sample notes'}]
        out = prepare(self.root / 'timelines', self.report, self.root, template='business')
        self.assertEqual([item['layout'] for item in json.loads((out / 'report.json').read_text())['sections']].count('timeline'), 2)
        self.assertIn("buildMilestones(root, items, section.id)", (out / 'site.js').read_text())
        broken = json.loads(json.dumps(self.report))
        broken['sections'][-1]['items'][0].pop('date')
        with self.assertRaises(ValueError):
            prepare(self.root / 'invalid-timeline', broken, self.root, template='business')
        broken = json.loads(json.dumps(self.report))
        broken['sections'][-1]['items'][0]['source'] = []
        with self.assertRaises(ValueError):
            prepare(self.root / 'invalid-source', broken, self.root, template='business')


if __name__ == '__main__':
    unittest.main()
