"""Behavior checks for portable packaging and safe output handling."""
import json
from pathlib import Path
import tempfile
import unittest
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
        self.assertEqual(json.loads((out / 'report.json').read_text()), self.report)
        payload = (out / 'report.js').read_text().removeprefix('window.weeklyStatus = ').strip().removesuffix(';')
        self.assertEqual(json.loads(payload), self.report)
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


if __name__ == '__main__':
    unittest.main()
