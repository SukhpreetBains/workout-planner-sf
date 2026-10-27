"""Regression checks for kickoff presets, evidence, and safe output generation."""
import json
from pathlib import Path
import tempfile
import unittest
from prepare import prepare, validate, TYPE, PRESETS


class KickoffTests(unittest.TestCase):
    def example(self):
        return json.loads((TYPE / 'templates/example.json').read_text())

    def test_each_depth_packages_only_its_outline(self):
        with tempfile.TemporaryDirectory() as temp:
            for depth, ids in PRESETS.items():
                output = Path(temp) / depth
                page = prepare(output, depth=depth)
                report = json.loads((output / 'report.json').read_text())
                self.assertEqual([s['id'] for s in report['sections']], ids)
                self.assertTrue(page.is_file())
                for asset in ('regular.woff2', 'bold.woff2', 'logo.svg', 'telescope.svg'):
                    self.assertTrue((output / 'assets' / asset).is_file())
                with self.assertRaises(FileExistsError):
                    prepare(output)

    def test_unconfirmed_claim_can_have_no_evidence(self):
        report = self.example()
        report['sections'][0]['items'][0]['source'] = []
        validate(report)
        report['sections'][0]['items'][0]['state'] = 'confirmed'
        with self.assertRaisesRegex(ValueError, 'need evidence'):
            validate(report)

    def test_reject_invalid_content(self):
        for key, value in [('depth', 'arbitrary'), ('secondaryColor', {}), ('sections', []), ('sample', 'false')]:
            report = self.example()
            report[key] = value
            with self.assertRaises(ValueError):
                validate(report)
        report = self.example()
        report['sections'][1]['id'] = 'opening'
        with self.assertRaises(ValueError):
            validate(report)

    def test_unknown_tracker_id_does_not_leave_output(self):
        report = self.example()
        report['sections'][0]['items'][0]['source'] = ['OBJ-999']
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'draft'
            with self.assertRaisesRegex(ValueError, 'project root'):
                prepare(output, report)
            self.assertFalse(output.exists())

    def test_real_content_packages_safe_document_snapshot(self):
        report = self.example()
        report['sample'] = False
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'workspace').mkdir()
            (root / 'workspace/brief.md').write_text('Approved kickoff evidence: <not markup>')
            report['sections'][0]['items'][0]['source'] = ['workspace/brief.md']
            output = root / 'draft'
            prepare(output, report, root)
            packaged = json.loads((output / 'report.json').read_text())
            entry = packaged['sourceDetails']['workspace/brief.md']['documents'][0]
            snapshot = output / 'presentation' / entry['link']
            self.assertIn('&lt;not markup&gt;', snapshot.read_text())
            self.assertEqual(len(packaged['sections']), len(report['sections']))

    def test_real_content_requires_workspace(self):
        report = self.example()
        report['sample'] = False
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'project-root'):
                prepare(Path(temp) / 'draft', report)

    def test_authored_depth_mismatch_and_unsafe_links(self):
        report = self.example()
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'match'):
                prepare(Path(temp) / 'draft', report, depth='executive')
            report['sourceLinks'] = {'bad': 'javascript:alert(1)'}
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                prepare(Path(temp) / 'draft', report)


if __name__ == '__main__':
    unittest.main()
