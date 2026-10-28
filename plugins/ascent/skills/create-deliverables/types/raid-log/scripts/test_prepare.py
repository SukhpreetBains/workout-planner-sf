"""Regression checks for RAID log collection, validation, and packaging."""
import json
from pathlib import Path
import tempfile
import unittest
import yaml
from collect import collect
from prepare import TYPE, prepare, validate

ROWS = {
    'person': [{'Person ID': 'PER-001', 'Name': 'Jordan Lee', 'Status': 'active'}],
    'workstream': [{'Workstream ID': 'WST-001', 'Name': 'Data migration', 'Status': 'active'}],
    'risk': [{'Risk ID': 'RSK-001', 'Name': 'Credentials may be late', 'Description': 'Access may slip UAT.',
              'Status': 'active', 'Date': '2026-10-02 00:00:00', 'Target Date': '2026-11-10 00:00:00',
              'Calculated Severity': 'Sev 1', 'Relationships': 'owned_by: PER-001; impacts: WST-001',
              'Source Refs': 'workspace/meetings/notes.md'}],
    'action_item': [{'Action Item ID': 'ACT-001', 'Name': 'Confirm access date', 'Description': 'Ask client IT.',
                     'Status': 'assigned', 'Target Date': '2026-10-30 00:00:00',
                     'Relationships': 'addresses: RSK-001; owned_by: PER-001'}],
}
PROPOSALS = {'updates': [
    {'category': 'dependency', 'proposal_id': 'p-dep', 'action': 'add',
     'fields': {'Name': 'UAT needs a sandbox', 'Description': 'UAT cannot start until the sandbox exists.', 'Status': 'pending'},
     'evidence': [{'source_ref': 'workspace/meetings/notes.md', 'excerpt': 'UAT cannot start until the sandbox exists.'}],
     'source_refs': ['workspace/meetings/notes.md'], 'review': {'state': 'pending'}},
    {'category': 'open_question', 'proposal_id': 'p-qst', 'action': 'add',
     'fields': {'Name': 'Migrate closed cases?', 'Description': 'Still to decide.'}, 'review': {'state': 'flagged'}},
    {'category': 'risk', 'proposal_id': 'p-chg', 'action': 'update', 'id': 'RSK-001',
     'fields': {'Status': 'mitigated'}, 'review': {'state': 'pending'}},
]}


def project(root):
    system = root / 'workspace/.system'
    for folder in ('tracker-copies', 'proposed-updates', 'applied-updates'):
        (system / folder).mkdir(parents=True)
    for category, rows in ROWS.items():
        (system / 'tracker-copies' / f'{category}.yaml').write_text(yaml.safe_dump({'category': category, 'rows': rows}))
    (system / 'proposed-updates/2026-10-28-notes.yaml').write_text(yaml.safe_dump(PROPOSALS))
    (system / 'project.yaml').write_text('account: Fictional client\nopportunity: Fictional programme\n')
    (root / 'workspace/meetings').mkdir(parents=True)
    (root / 'workspace/meetings/notes.md').write_text('UAT cannot start until the sandbox exists.\n')
    return root


def completed(root):
    log = collect(root, '2026-10-28')
    log['secondaryColor'] = {'name': 'Cyan', 'hex': '#1BE1F2'}
    log['coverageNote'] = 'Fictional fixture.'
    return log


class RaidLogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = project(Path(self.temp.name) / 'project')

    def tearDown(self):
        self.temp.cleanup()

    def item(self, log, key):
        return next(i for i in log['items'] if i['key'] == key)

    def test_collect_resolves_recorded_values_and_includes_pending_items(self):
        log = collect(self.root, '2026-10-28')
        self.assertEqual(log['project'], 'Fictional programme')
        risk = self.item(log, 'RSK-001')
        self.assertEqual(risk['owner'], {'value': 'Jordan Lee', 'basis': 'recorded', 'from': ['PER-001']})
        self.assertEqual(risk['impactArea']['value'], 'Data migration')
        self.assertEqual(risk['severity']['value'], 'High')
        self.assertEqual((risk['dateRaised']['value'], risk['target']['value']), ('2026-10-02', '2026-11-10'))
        self.assertEqual(risk['nextAction'], {'value': 'Confirm access date', 'basis': 'recorded', 'from': ['ACT-001']})
        self.assertEqual(risk['pendingChanges'], ['p-chg'])
        dependency = self.item(log, 'p-dep')
        self.assertEqual((dependency['review'], dependency['id'], dependency['source']), ('pending', None, ['proposal:p-dep']))
        question = self.item(log, 'p-qst')
        self.assertEqual((question['tab'], question['status']), ('decisions', 'open'))
        self.assertNotIn('severity', question)
        self.assertNotIn('p-chg', {i['key'] for i in log['items']})

    def test_project_log_packages_sources_with_tones_and_vocabulary(self):
        log = completed(self.root)
        output = Path(self.temp.name) / 'out'
        page = prepare(output, log, self.root)
        self.assertTrue(page.is_file())
        built = json.loads((output / 'raid.json').read_text())
        risk = self.item(built, 'RSK-001')
        self.assertEqual((risk['open'], risk['tone']), (True, 'attention'))
        self.assertEqual(built['vocabulary']['levels']['importance']['Critical'], {'color': 'red', 'squares': 2})
        pending = built['sourceDetails']['proposal:p-dep']
        self.assertEqual(pending['review'], 'pending')
        link = pending['evidence'][0]['link']
        self.assertTrue(link.startswith('sources/') and (output / link).is_file())
        for asset in ('regular.woff2', 'bold.woff2', 'logo.svg'):
            self.assertTrue((output / 'assets' / asset).is_file())
        with self.assertRaises(FileExistsError):
            prepare(output, log, self.root)

    def test_every_item_must_appear_or_be_omitted_with_a_reason(self):
        log = completed(self.root)
        log['items'] = [i for i in log['items'] if i['key'] != 'p-qst']
        with self.assertRaisesRegex(ValueError, 'missing without an omitted reason'):
            prepare(Path(self.temp.name) / 'a', log, self.root)
        log['omitted'] = [{'key': 'p-qst', 'reason': 'Duplicate of an approved question.'}]
        prepare(Path(self.temp.name) / 'b', log, self.root)

    def test_status_must_match_the_current_record(self):
        log = completed(self.root)
        self.item(log, 'RSK-001')['status'] = 'closed'
        with self.assertRaisesRegex(ValueError, 'status must match'):
            prepare(Path(self.temp.name) / 'out', log, self.root)

    def test_field_values_follow_the_picklists_and_basis_rules(self):
        cases = [
            ('priority', {'value': 'P1', 'basis': 'stated', 'source': ['workspace/meetings/notes.md']}, 'canonical'),
            ('priority', {'value': 'High', 'basis': 'assessed', 'source': ['workspace/meetings/notes.md']}, 'reason'),
            ('owner', {'value': 'Jordan Lee', 'basis': 'assessed', 'reason': 'x', 'source': ['a']}, 'basis'),
            ('target', {'value': '11/10/2026', 'basis': 'stated', 'source': ['a']}, 'YYYY-MM-DD'),
            ('importance', None, 'not used on Risks'),
        ]
        for key, value, message in cases:
            log = completed(self.root)
            self.item(log, 'RSK-001')[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, message):
                validate(log)

    def test_excel_export_has_one_sheet_per_tab_with_marked_values(self):
        from openpyxl import load_workbook
        log = completed(self.root)
        self.item(log, 'RSK-001')['priority'] = {'value': 'High', 'basis': 'assessed', 'reason': 'Blocks UAT start.',
                                                 'source': ['workspace/meetings/notes.md']}
        output = Path(self.temp.name) / 'out'
        prepare(output, log, self.root)
        built = json.loads((output / 'raid.json').read_text())
        self.assertEqual(built['exportFile'], 'raid-log-fictional-programme-2026-10-28.xlsx')
        book = load_workbook(output / built['exportFile'])
        self.assertEqual(book.sheetnames, ['Summary', 'Risks', 'Assumptions', 'Issues', 'Decisions', 'Dependencies', 'Actions'])
        risks = book['Risks']
        headers = [c.value for c in risks[1]]
        self.assertNotIn('Importance', headers)
        self.assertNotIn('Sources', headers)
        row = {h: c for h, c in zip(headers, risks[2])}
        self.assertEqual((row['RAID ID'].value, row['Type'].value, row['Status'].value), ('RSK-001', 'Risk', 'Active'))
        self.assertEqual(row['Priority'].value, 'High (assessed)')
        self.assertIn('Blocks UAT start.', row['Priority'].comment.text)
        self.assertEqual(row['Target / required by'].number_format, 'mm/dd/yyyy')
        decisions = book['Decisions']
        self.assertEqual([c.value for c in decisions[2]][:2], ['Pending', 'Decision needed'])
        self.assertEqual(decisions.cell(2, 6).value, 'Pending review')

    def test_sample_needs_no_project_and_real_logs_do(self):
        output = Path(self.temp.name) / 'sample'
        prepare(output)
        self.assertTrue(json.loads((output / 'raid.json').read_text())['sample'])
        log = json.loads((TYPE / 'templates/example.json').read_text())
        log['sample'] = False
        with self.assertRaisesRegex(ValueError, 'project-root'):
            prepare(Path(self.temp.name) / 'real', log)


if __name__ == '__main__':
    unittest.main()
