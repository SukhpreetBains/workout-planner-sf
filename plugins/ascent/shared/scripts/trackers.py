"""Read and write the tracker workbooks (openpyxl helpers)."""

from __future__ import annotations

from copy import copy
from datetime import date, datetime, timezone
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


def is_relationships(column: dict) -> bool:
    return column.get("type") == "relationships"


def parse_relationships(value: object) -> list[tuple[str, str]]:
    """Split a Relationships cell into (meaning, target ID) pairs.

    An entry without a colon is returned with an empty meaning so validation
    can report it rather than silently dropping it.
    """
    entries = []
    for part in str(value or "").split(";"):
        part = part.strip()
        if not part:
            continue
        meaning, separator, target = part.partition(":")
        entries.append((meaning.strip(), target.strip()) if separator else ("", part))
    return entries


def format_relationships(entries: list[tuple[str, str]]) -> str:
    return "; ".join(dict.fromkeys(f"{meaning}: {target}" for meaning, target in entries))


def normalize_enum(value: object) -> str:
    """Normalize human labels such as ``Very High`` to schema enum keys."""
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def coerce_value(column: dict, value: object) -> object:
    """Convert schema-typed values before they are written to Excel."""
    if value in (None, ""):
        return ""
    if column.get("type") == "number":
        return float(value)
    if column.get("type") == "date":
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        return datetime.fromisoformat(str(value).strip())
    if "enum" in column:
        return normalize_enum(value)
    return value


def apply_computed_fields(category: str, fields: dict, schema: dict) -> None:
    """Fill computed fields only when all inputs are supplied on this write."""
    columns = schema["categories"][category]["columns"]
    if not any(c.get("computed") == "risk_score" for c in columns):
        return
    probability = fields.get("Probability")
    impact = fields.get("Impact")
    if probability in (None, "") or impact in (None, ""):
        return
    impact_col = next(c for c in columns if c["name"] == "Impact")
    weight = impact_col["weights"].get(normalize_enum(impact))
    if weight is None:
        return
    score = float(probability) * float(weight)
    fields["Risk Score"] = score
    fields["Calculated Severity"] = (
        "Sev 1" if score >= 0.5 else "Sev 2" if score >= 0.2 else "Sev 3"
    )


def has_rows(ws) -> bool:
    return any(any(value not in (None, "") for value in row)
               for row in ws.iter_rows(min_row=2, values_only=True))


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
                if have != want and (reset and ws.max_row <= 1):
                    ws.delete_rows(1, ws.max_row)
                    ws.append(want)
                    changed.append(f"reset header of '{tab}' in {tracker['file']}")
                else:
                    for name in want:
                        if name in have:
                            continue
                        new_col = ws.max_column + 1
                        source = ws.cell(1, max(1, new_col - 1))
                        target = ws.cell(1, new_col, name)
                        if source.has_style:
                            target._style = copy(source._style)
                        if source.font:
                            target.font = copy(source.font)
                        if source.fill:
                            target.fill = copy(source.fill)
                        if source.border:
                            target.border = copy(source.border)
                        if source.alignment:
                            target.alignment = copy(source.alignment)
                        changed.append(f"added column '{name}' to '{tab}' in {tracker['file']}")
                        have.append(name)
        for tab in tracker.get("retired_tabs", []):
            if tab in wb.sheetnames and len(wb.sheetnames) > 1 and not has_rows(wb[tab]):
                del wb[tab]
                changed.append(f"removed empty retired tab '{tab}' from {tracker['file']}")
        # Other unknown tabs and custom columns are user-owned and are never removed.
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
    init_trackers(schema)
    path = REPO_ROOT / cat["tracker_file"]
    wb = load_workbook(path)
    ws = wb[cat["tab"]]
    cols = [c.value for c in ws[1] if c.value]
    idcol = id_column(category, schema)
    stamp = now_iso()

    fields = dict(fields)
    apply_computed_fields(category, fields, schema)
    definitions = {column["name"]: column for column in cat["columns"]}
    fields = {
        name: coerce_value(definitions[name], value) if name in definitions else value
        for name, value in fields.items()
    }
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
    for name, column in definitions.items():
        if name not in cols:
            continue
        cell = ws.cell(target[0].row if target else ws.max_row, cols.index(name) + 1)
        if column.get("type") == "date" and cell.value not in (None, ""):
            cell.number_format = "yyyy-mm-dd"
        if column.get("type") == "number" and cell.value not in (None, ""):
            cell.number_format = "0.00"
    wb.save(path)
    return row_id


def delete_row(category: str, tracker_id: str, schema: dict) -> None:
    """Remove one accepted tracker row by its stable ID."""
    cat = schema["categories"][category]
    path = REPO_ROOT / cat["tracker_file"]
    if not path.exists():
        raise ValueError(f"{category} tracker does not exist")
    wb = load_workbook(path)
    try:
        if cat["tab"] not in wb.sheetnames:
            raise ValueError(f"{category} tracker tab does not exist")
        ws = wb[cat["tab"]]
        cols = [c.value for c in ws[1] if c.value]
        identifier = id_column(category, schema)
        for row in ws.iter_rows(min_row=2):
            if str(row[cols.index(identifier)].value or "") == tracker_id:
                ws.delete_rows(row[0].row, 1)
                wb.save(path)
                return
        raise ValueError(f"{category} row {tracker_id} was not found")
    finally:
        wb.close()
