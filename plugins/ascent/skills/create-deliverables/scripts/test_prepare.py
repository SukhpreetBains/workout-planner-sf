"""Behavior checks for portable packaging and safe output handling."""
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from prepare import prepare, validate, SKILL
from verify_assets import verify


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        script = (SKILL / 'types/weekly-status/templates/report.js').read_text()
        self.report = json.loads(script.removeprefix('window.weeklyStatus = ').strip().removesuffix(';'))

    def test_package_preserves_report_and_local_dependencies(self):
        self.report['summary'] = '</script><img src=x onerror=alert(1)> and Ω'
        out = prepare(self.root / 'site', self.report)
        self.assertEqual(json.loads((out / 'report.json').read_text())['summary'], self.report['summary'])
        self.assertEqual([section['id'] for section in json.loads((out / 'report.json').read_text())['sections']], ['accomplishments', 'next-steps', 'milestones', 'risks-and-decisions'])
        payload = (out / 'report.js').read_text().removeprefix('window.weeklyStatus = ').strip().removesuffix(';')
        self.assertEqual(json.loads(payload), json.loads((out / 'report.json').read_text()))
        for name in ('business', 'expressive', 'animated'):
            self.assertTrue((out / name / 'index.html').is_file())
        for name in ('regular.woff2', 'bold.woff2', 'logo.svg', 'illustration.svg', 'whiteboard.svg', 'pointing.svg', 'high-five.svg', 'telescope.svg', 'anime.esm.min.js', 'LICENSE.md'):
            self.assertGreater((out / 'assets' / name).stat().st_size, 0)
        self.assertEqual(len(list((out / 'assets/iconography').glob('*.svg'))), 102)
        verify(out)

    def test_existing_output_is_untouched(self):
        out = self.root / 'site'
        out.mkdir()
        (out / 'keep').write_text('user work')
        with self.assertRaises(FileExistsError):
            prepare(out, self.report)
        self.assertEqual((out / 'keep').read_text(), 'user work')

    def test_invalid_input_creates_no_output(self):
        del self.report['risks'][0]['source']
        with self.assertRaises(ValueError):
            prepare(self.root / 'site', self.report)
        self.assertFalse((self.root / 'site').exists())

    def test_empty_sections_are_valid(self):
        for key in ('accomplishments', 'nextSteps', 'milestones', 'risks', 'decisions'):
            self.report[key] = []
        self.assertEqual(validate(self.report), self.report)

    def test_missing_icon_is_detected(self):
        out = prepare(self.root / 'site', self.report)
        (out / 'assets/iconography/cloud.svg').unlink()
        with self.assertRaises(ValueError):
            verify(out)

    def test_reasoned_health_needs_cited_basis(self):
        del self.report['healthSource']
        with self.assertRaises(ValueError):
            validate(self.report)

    def test_no_icon_package_when_disabled(self):
        self.report['useIconography'] = False
        out = prepare(self.root / 'site', self.report)
        self.assertFalse((out / 'assets/iconography').exists())
        verify(out)

    def test_sample_package_has_report_json(self):
        out = prepare(self.root / 'sample')
        self.assertTrue(json.loads((out / 'report.json').read_text())['sample'])
        verify(out)

    def test_sample_cli_works_without_site_packages(self):
        out = self.root / 'stdlib-sample'
        command = [sys.executable, '-S', str(SKILL / 'scripts/prepare.py'), str(out)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads((out / 'report.json').read_text())['sample'])

    def test_project_cli_explains_missing_yaml_dependency(self):
        out = self.root / 'needs-yaml'
        command = [sys.executable, '-S', str(SKILL / 'scripts/prepare.py'), str(out), '--project-root', str(self.root)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires PyYAML', result.stderr)
        self.assertIn('shared/scripts/py', result.stderr)
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
