"""Read and write the tracker workbooks (openpyxl helpers)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook, load_workbook

from paths import REPO_ROOT, load_schema

MANAGED_COLUMNS = ["Source Refs", "Notes", "Created At", "Updated At"]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def id_column(category: str, schema: dict) -> str:
    return category.replace("_", " ").title() + " ID"


def header(category: str, schema: dict) -> list[str]:
    cat = schema["categories"][category]
    cols = [id_column(category, schema)]
    cols += [c["name"] for c in cat["columns"]]
    cols += MANAGED_COLUMNS
    return cols


def init_trackers(schema: dict | None = None, reset: bool = False) -> list[str]:
    """Create tracker workbooks/tabs that are missing. Never touches existing
    rows unless reset=True (which rebuilds headers on empty tabs only)."""
    schema = schema or load_schema()
    changed: list[str] = []
    for tracker in schema["trackers"].values():
        path = REPO_ROOT / tracker["file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            wb = load_workbook(path)
        else:
            wb = Workbook()
            wb.remove(wb.active)
            changed.append(f"created {tracker['file']}")
        for cat in tracker["tabs"]:
            tab = schema["categories"][cat]["tab"]
            want = header(cat, schema)
            if tab not in wb.sheetnames:
                ws = wb.create_sheet(tab)
                ws.append(want)
                changed.append(f"added tab '{tab}' to {tracker['file']}")
            else:
                ws = wb[tab]
                have = [c.value for c in ws[1] if c.value]
                if have != want and (reset or ws.max_row <= 1):
                    ws.delete_rows(1, ws.max_row)
                    ws.append(want)
                    changed.append(f"reset header of '{tab}' in {tracker['file']}")
        # drop tabs the schema does not know about only if they are empty
        known = {schema["categories"][c]["tab"] for c in tracker["tabs"]}
        for name in list(wb.sheetnames):
            if name not in known and wb[name].max_row <= 1:
                wb.remove(wb[name])
                changed.append(f"removed empty unknown tab '{name}' from {tracker['file']}")
        wb.save(path)
    return changed


def read_rows(category: str, schema: dict | None = None) -> list[dict]:
    """All rows of a category as dicts keyed by column name."""
    schema = schema or load_schema()
    cat = schema["categories"][category]
    path = REPO_ROOT / cat["tracker_file"]
    if not path.exists():
        return []
    wb = load_workbook(path, read_only=True)
    if cat["tab"] not in wb.sheetnames:
        return []
    ws = wb[cat["tab"]]
    rows_iter = ws.iter_rows(values_only=True)
    cols = [c for c in next(rows_iter, []) if c]
    out = []
    for values in rows_iter:
        row = {col: ("" if v is None else str(v)) for col, v in zip(cols, values)}
        if any(v.strip() for v in row.values()):
            out.append(row)
    wb.close()
    return out


def next_id(category: str, schema: dict) -> str:
    prefix = schema["categories"][category]["id_prefix"]
    col = id_column(category, schema)
    highest = 0
    for row in read_rows(category, schema):
        rid = row.get(col, "")
        if rid.startswith(prefix) and rid[len(prefix):].isdigit():
            highest = max(highest, int(rid[len(prefix):]))
    return f"{prefix}{highest + 1:03d}"


def upsert_row(category: str, fields: dict, schema: dict) -> str:
    """Insert (no ID key) or update (ID key present) one row. Returns the ID."""
    cat = schema["categories"][category]
    path = REPO_ROOT / cat["tracker_file"]
    if not path.exists():
        init_trackers(schema)
    wb = load_workbook(path)
    ws = wb[cat["tab"]]
    cols = [c.value for c in ws[1] if c.value]
    idcol = id_column(category, schema)
    stamp = now_iso()

    row_id = fields.get(idcol, "")
    target = None
    if row_id:
        for row in ws.iter_rows(min_row=2):
            if str(row[cols.index(idcol)].value or "") == row_id:
                target = row
                break
        if target is None:
            raise ValueError(f"{category} row {row_id} not found for update")
        for name, value in fields.items():
            if name in cols and name != idcol:
                target[cols.index(name)].value = value
        target[cols.index("Updated At")].value = stamp
    else:
        row_id = next_id(category, schema)
        values = {**fields, idcol: row_id, "Created At": stamp, "Updated At": stamp}
        ws.append([values.get(c, "") for c in cols])
    wb.save(path)
    return row_id
