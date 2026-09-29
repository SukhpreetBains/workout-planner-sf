"""Converter fidelity: table order, tracked changes, PowerPoint tables and groups.

Run with the project environment:
    plugins/ascent/shared/scripts/py -m unittest discover -s plugins/ascent/shared/scripts
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import read_document  # noqa: E402

REDLINE_PARAGRAPH = (
    '<w:p {ns}><w:r><w:t xml:space="preserve">The fee is </w:t></w:r>'
    '<w:ins w:id="1" w:author="Experian Legal" w:date="2026-07-07T00:00:00Z">'
    '<w:r><w:t>fixed</w:t></w:r></w:ins>'
    '<w:del w:id="2" w:author="Experian Legal" w:date="2026-07-07T00:00:00Z">'
    '<w:r><w:delText>variable</w:delText></w:r></w:del>'
    '<w:r><w:t xml:space="preserve"> per month.</w:t></w:r></w:p>'
)


class ReadDocxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import docx
        from docx.oxml import parse_xml
        from docx.oxml.ns import nsdecls

        cls.tmp = tempfile.TemporaryDirectory()
        doc = docx.Document()
        doc.add_heading("Roles", level=1)
        table = doc.add_table(rows=2, cols=2)
        for cell, text in zip(table._cells, ["Role", "Owner", "Architect", "Ruturaj"]):
            cell.text = text
        doc.add_heading("Commercials", level=1)
        anchor = doc.add_paragraph("")
        anchor._p.addprevious(parse_xml(REDLINE_PARAGRAPH.format(ns=nsdecls("w"))))
        anchor._p.getparent().remove(anchor._p)
        cell = doc.add_table(rows=1, cols=1)._cells[0]
        cell._tc.remove(cell.paragraphs[0]._p)
        cell._tc.append(parse_xml(REDLINE_PARAGRAPH.format(ns=nsdecls("w"))))
        path = Path(cls.tmp.name) / "redline.docx"
        doc.save(path)
        cls.text = read_document.read_docx(path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_tables_stay_under_their_own_heading(self):
        roles, table, commercials = (self.text.index(s) for s in ("# Roles", "| Architect | Ruturaj |", "# Commercials"))
        self.assertLess(roles, table)
        self.assertLess(table, commercials)

    def test_body_shows_the_edited_wording(self):
        body = self.text.split("## Tracked changes")[0]
        self.assertIn("The fee is fixed per month.", body)
        self.assertIn("| The fee is fixed per month. |", body)
        self.assertNotIn("variable", body)

    def test_tracked_changes_are_listed_with_authors(self):
        log = self.text.split("## Tracked changes", 1)[1]
        self.assertIn('- Inserted by Experian Legal: "fixed"', log)
        self.assertIn('- Deleted by Experian Legal: "variable"', log)

    def test_document_without_changes_has_no_change_log(self):
        import docx

        path = Path(self.tmp.name) / "plain.docx"
        doc = docx.Document()
        doc.add_paragraph("Nothing changed here.")
        doc.save(path)
        self.assertNotIn("Tracked changes", read_document.read_docx(path))


class ReadPptxTest(unittest.TestCase):
    def test_tables_and_grouped_shapes_are_read(self):
        from pptx import Presentation
        from pptx.util import Inches

        with tempfile.TemporaryDirectory() as tmp:
            deck = Presentation()
            slide = deck.slides.add_slide(deck.slide_layouts[6])
            slide.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1)).text_frame.text = "Delivery risks"
            table = slide.shapes.add_table(2, 2, Inches(1), Inches(2), Inches(4), Inches(1)).table
            for cell, text in zip((c for row in table.rows for c in row.cells),
                                  ["Risk", "Impact", "Data quality delays", "Med"]):
                cell.text = text
            group = slide.shapes.add_group_shape()
            group.shapes.add_textbox(Inches(1), Inches(4), Inches(3), Inches(1)).text_frame.text = "Grouped note"
            path = Path(tmp) / "deck.pptx"
            deck.save(path)
            text = read_document.read_pptx(path)

        self.assertIn("- Delivery risks", text)
        self.assertIn("| Data quality delays | Med |", text)
        self.assertIn("- Grouped note", text)


if __name__ == "__main__":
    unittest.main()
