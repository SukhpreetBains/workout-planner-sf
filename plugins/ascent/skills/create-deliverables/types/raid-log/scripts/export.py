"""Write a RAID log as an Excel workbook a user can send on, one sheet per RAID tab."""
from datetime import date
import re
from picklists import fields_for

HEADER_FILL = '002FAF'
PENDING_FILL = 'FFE27A'
OVERDUE_RED = 'D32F2F'


def workbook_name(log):
    slug = re.sub(r'[^a-z0-9]+', '-', log['project'].lower()).strip('-') or 'project'
    return f'raid-log-{slug}-{log["asOf"]}.xlsx'


def write_workbook(log, picklists, schema, path):
    try:
        from openpyxl import Workbook
        from openpyxl.comments import Comment
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError as error:
        raise ValueError('Excel export requires openpyxl. Run preparation with the Ascent shared/scripts/py launcher.') from error
    book = Workbook()
    summary = book.active
    summary.title = 'Summary'
    rows = [('RAID log', log['project']), ('As of', date.fromisoformat(log['asOf'])), ('', '')]
    for tab in picklists['tabs']:
        items = [i for i in log['items'] if i['tab'] == tab['id']]
        rows.append((tab['label'], f'{sum(i["open"] for i in items)} open of {len(items)}'))
    rows += [('', ''),
             ('Pending review', 'Not yet approved in the project review inbox.'),
             ('(assessed)', 'A judgment against the RAID picklist definitions, not stated in the sources. The cell comment gives the reasoning.')]
    for row in rows:
        summary.append(row)
    summary['B2'].number_format = 'mm/dd/yyyy'
    summary['B2'].alignment = Alignment(horizontal='left')
    summary['A1'].font = summary['B1'].font = Font(bold=True, size=14)
    for cell in summary['A']:
        cell.font = Font(bold=True, size=cell.font.size)
    summary.column_dimensions['A'].width = 18
    summary.column_dimensions['B'].width = 90

    # A link field names other items; give each one's ID so readers can find its row.
    linked = {i['key']: f'{i["title"]} ({i["id"] or "pending review"})' for i in log['items']}
    for tab in picklists['tabs']:
        sheet = book.create_sheet(tab['label'])
        fields = fields_for(picklists, tab['id'])
        headers = ['RAID ID', 'Type', 'Item', 'Description', 'Status', 'Review'] + [f['label'] for f in fields]
        sheet.append(headers)
        for cell in sheet[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor=HEADER_FILL)
            cell.alignment = Alignment(vertical='center', wrap_text=True)
        for item in (i for i in log['items'] if i['tab'] == tab['id']):
            kind = tab.get('kinds', {}).get(item['category']) or schema['categories'][item['category']]['label']
            values = [item['id'] or 'Pending', kind, item['title'], item['description'],
                      item['status'].replace('_', ' ').capitalize(),
                      'Pending review' if item['review'] == 'pending' else 'Approved']
            notes = {}
            for column, field in enumerate(fields, start=len(values) + 1):
                value = item.get(field['key'])
                if not value:
                    values.append(None)
                elif field.get('type') == 'date':
                    values.append(date.fromisoformat(value['value']))
                elif field.get('link'):
                    values.append('; '.join(linked.get(key, key) for key in value['from']))
                elif value['basis'] == 'assessed':
                    values.append(value['value'] + ' (assessed)')
                    notes[column] = value['reason']
                else:
                    values.append(value['value'])
            sheet.append(values)
            row = sheet.max_row
            for column, reason in notes.items():
                sheet.cell(row, column).comment = Comment('Assessed: ' + reason, 'Ascent', width=320, height=110)
            overdue = item['open'] and item.get('target') and item['target']['value'] < log['asOf']
            for column, field in enumerate(fields, start=7):
                if field.get('type') == 'date':
                    sheet.cell(row, column).number_format = 'mm/dd/yyyy'
                if field['key'] == 'target' and overdue:
                    sheet.cell(row, column).font = Font(color=OVERDUE_RED, bold=True)
            if item['review'] == 'pending':
                sheet.cell(row, 6).fill = PatternFill('solid', fgColor=PENDING_FILL)
            for cell in sheet[row]:
                cell.alignment = Alignment(vertical='top', wrap_text=True)
        widths = [12, 16, 36, 60, 14, 15] + [14 if f.get('type') == 'date' or 'picklist' in f else 30 for f in fields]
        for column, width in enumerate(widths, start=1):
            sheet.column_dimensions[sheet.cell(1, column).column_letter].width = width
        sheet.freeze_panes = 'C2'
        sheet.auto_filter.ref = sheet.dimensions
    book.save(path)
    return path
