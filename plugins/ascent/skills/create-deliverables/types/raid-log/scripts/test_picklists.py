"""Keep the RAID log picklists complete and aligned with the tracker schema."""
import unittest
from picklists import TYPE, from_tracker, is_open, level_value, load, tone, tracker_statuses

COLORS = {'red', 'amber', 'green', 'grey'}


class PicklistTests(unittest.TestCase):
    def setUp(self):
        self.picklists = load()
        self.statuses = tracker_statuses()

    def test_tabs_cover_the_raid_categories_once(self):
        tabs = self.picklists['tabs']
        self.assertEqual([t['id'] for t in tabs], ['risks', 'assumptions', 'issues', 'decisions', 'dependencies', 'actions'])
        categories = [c for t in tabs for c in t['categories']]
        self.assertEqual(len(categories), len(set(categories)))
        self.assertEqual(set(categories), set(self.picklists['status']))

    def test_every_tracker_status_is_open_or_closed_exactly_once(self):
        for category, groups in self.picklists['status'].items():
            listed = groups['open'] + groups['closed']
            self.assertEqual(len(listed), len(set(listed)), category)
            self.assertEqual(set(listed), set(self.statuses[category]), category)
            self.assertEqual(set(groups['tone']), set(listed), category)
            self.assertTrue(set(groups['tone'].values()) <= set(self.picklists['tones']), category)
        for tone_name, definition in self.picklists['tones'].items():
            self.assertIn(definition['color'], COLORS, tone_name)

    def test_level_tabs_and_values_are_well_formed(self):
        tab_ids = {t['id'] for t in self.picklists['tabs']}
        for name, level in self.picklists['levels'].items():
            self.assertTrue(set(level['tabs']) <= tab_ids, name)
            aliases = [a for v in level['values'] for a in v['aliases']]
            self.assertEqual(len(aliases), len(set(aliases)), name)
            # Levels are colored scales; a category picklist such as impact area has no colors.
            colored = name in ('priority', 'severity', 'importance')
            for entry in level['values']:
                self.assertTrue(entry['definition'].strip(), name)
                if colored:
                    self.assertIn(entry['color'], COLORS, name)
                else:
                    self.assertNotIn('color', entry, name)
                self.assertTrue(all(a == a.lower() for a in entry['aliases']), name)
            for category, rule in level.get('from_tracker', {}).items():
                values = {v['value'] for v in level['values']}
                self.assertTrue(set(rule['map'].values()) <= values, name)

    def test_readme_lists_every_picklist_file(self):
        folder = TYPE / 'picklists'
        readme = (folder / 'README.md').read_text(encoding='utf-8')
        for path in folder.glob('*.yaml'):
            self.assertIn(f'`{path.name}`', readme)

    def test_values_and_source_wording_map_to_one_level(self):
        self.assertEqual(level_value(self.picklists, 'priority', 'P1'), 'High')
        self.assertEqual(level_value(self.picklists, 'severity', 'Sev 2'), 'Medium')
        self.assertEqual(level_value(self.picklists, 'importance', 'critical'), 'Critical')
        self.assertEqual(level_value(self.picklists, 'impact-area', 'timeline_schedule'), 'Timeline / Schedule')
        self.assertEqual(level_value(self.picklists, 'impact-area', 'Unknown / TBD'), 'Unknown / TBD')
        with self.assertRaisesRegex(ValueError, 'Priority must be one of'):
            level_value(self.picklists, 'priority', 'Critical-ish')

    def test_calculated_risk_severity_maps_and_status_groups_resolve(self):
        self.assertEqual(from_tracker(self.picklists, 'severity', 'risk', {'Calculated Severity': 'Sev 1'}), 'High')
        self.assertEqual(from_tracker(self.picklists, 'impact-area', 'decision', {'Category': 'delivery_quality'}), 'Delivery Quality')
        self.assertEqual(len(self.picklists['levels']['impact-area']['values']), 11)
        self.assertIsNone(from_tracker(self.picklists, 'severity', 'issue', {}))
        self.assertTrue(is_open(self.picklists, 'dependency', 'blocked'))
        self.assertFalse(is_open(self.picklists, 'risk', 'realized'))
        self.assertEqual(tone(self.picklists, 'issue', 'resolved'), 'done')
        self.assertEqual(tone(self.picklists, 'dependency', 'blocked'), 'attention')
        with self.assertRaises(ValueError):
            is_open(self.picklists, 'issue', 'parked')


if __name__ == '__main__':
    unittest.main()
