"""Transactional item-level review operations for proposed tracker updates."""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import yaml

from paths import (
    AI_REVIEW_QUEUE,
    APPLIED_UPDATES_DIR,
    PROPOSED_UPDATES_DIR,
    REJECTED_UPDATES_DIR,
    REPO_ROOT,
    REVIEW_HISTORY,
    REVIEW_IDEMPOTENCY,
    REVIEW_LOCK,
    SYSTEM_DIR,
    TRACKER_COPIES_DIR,
    load_schema,
)
from trackers import id_column, read_rows, upsert_row
from validate_updates import validate


class ReviewError(RuntimeError):
    status = 400


class NotFound(ReviewError):
    status = 404


class RevisionConflict(ReviewError):
    status = 409


class ValidationFailure(ReviewError):
    status = 422

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def review_lock() -> Iterator[None]:
    SYSTEM_DIR.mkdir(parents=True, exist_ok=True)
    with open(REVIEW_LOCK, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_yaml(path: Path, value: dict) -> None:
    atomic_write_text(path, yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=100))


def load_yaml(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict) or not isinstance(value.get("updates"), list):
        raise ReviewError(f"{path.name} must contain an updates list")
    return value


def stable_id(path: Path, index: int, update: dict) -> str:
    seed = f"{path.resolve()}:{index}:{update.get('category', '')}:{update.get('id', '')}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def upgrade_document(path: Path, document: dict) -> bool:
    changed = False
    default_refs = document.get("source_refs") or []
    for index, update in enumerate(document["updates"]):
        if not update.get("proposal_id"):
            update["proposal_id"] = stable_id(path, index, update)
            changed = True
        if not isinstance(update.get("revision"), int) or update["revision"] < 1:
            update["revision"] = 1
            changed = True
        if "evidence" not in update:
            update["evidence"] = [
                {"source_ref": ref, "excerpt": ""}
                for ref in (update.get("source_refs") or default_refs)
            ]
            changed = True
        if "review" not in update:
            update["review"] = {"state": "pending"}
            changed = True
    return changed


def proposal_files() -> list[Path]:
    if not PROPOSED_UPDATES_DIR.exists():
        return []
    return sorted(path for path in PROPOSED_UPDATES_DIR.glob("*.y*ml") if path.is_file())


def find_item(proposal_id: str) -> tuple[Path, dict, int, dict]:
    for path in proposal_files():
        document = load_yaml(path)
        changed = upgrade_document(path, document)
        if changed:
            atomic_yaml(path, document)
        for index, update in enumerate(document["updates"]):
            if update.get("proposal_id") == proposal_id:
                return path, document, index, update
    raise NotFound(f"proposal {proposal_id} was not found")


def current_row(update: dict, schema: dict) -> dict | None:
    if update.get("action", "add") != "update" or not update.get("id"):
        return None
    category = update["category"]
    identifier = id_column(category, schema)
    return next((row for row in read_rows(category, schema)
                 if row.get(identifier) == update["id"]), None)


def list_cards() -> dict:
    schema = load_schema()
    cards = []
    with review_lock():
        for path in proposal_files():
            document = load_yaml(path)
            if upgrade_document(path, document):
                atomic_yaml(path, document)
            for update in document["updates"]:
                category = update.get("category", "")
                definition = schema["categories"].get(category, {})
                cards.append({
                    "proposal_id": update["proposal_id"],
                    "revision": update["revision"],
                    "category": category,
                    "category_label": category.replace("_", " ").title(),
                    "action": update.get("action", "add"),
                    "tracker_id": update.get("id"),
                    "fields": update.get("fields") or {},
                    "field_schema": definition.get("columns", []),
                    "source_refs": update.get("source_refs") or document.get("source_refs") or [],
                    "evidence": update.get("evidence") or [],
                    "review": update.get("review") or {"state": "pending"},
                    "current_row": current_row(update, schema),
                    "source_file": path.name,
                })
    counts: dict[str, int] = {}
    for card in cards:
        counts[card["category"]] = counts.get(card["category"], 0) + 1
    cards.sort(key=lambda card: (card.get("review", {}).get("state") != "flagged",
                                 card["category_label"], card["proposal_id"]))
    return {"cards": cards, "counts": counts, "remaining": len(cards)}


def check_revision(update: dict, revision: object) -> None:
    try:
        supplied = int(revision)
    except (TypeError, ValueError):
        raise RevisionConflict("a numeric revision is required")
    if supplied != update["revision"]:
        raise RevisionConflict(
            f"proposal changed from revision {supplied} to {update['revision']}; reload before saving"
        )


def append_history(event: str, update: dict, details: dict | None = None) -> dict:
    record = {
        "timestamp": now_iso(),
        "event": event,
        "proposal_id": update["proposal_id"],
        "revision": update["revision"],
        "category": update.get("category"),
        **(details or {}),
    }
    REVIEW_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with open(REVIEW_HISTORY, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def autosave(proposal_id: str, revision: object, fields: dict) -> dict:
    if not isinstance(fields, dict):
        raise ReviewError("fields must be an object")
    with review_lock():
        path, document, _index, update = find_item(proposal_id)
        check_revision(update, revision)
        candidate = dict(update)
        candidate["fields"] = fields
        problems = validate({"source_refs": document.get("source_refs") or [], "updates": [candidate]},
                            load_schema())
        update["fields"] = candidate["fields"]
        update["revision"] += 1
        atomic_yaml(path, document)
        append_history("edit", update, {"valid": not problems, "validation": problems})
        return {"proposal_id": proposal_id, "revision": update["revision"], "validation": problems}


def remove_and_archive(path: Path, document: dict, index: int, update: dict,
                       destination: Path, decision: str, note: str = "") -> None:
    destination.mkdir(parents=True, exist_ok=True)
    archive = {
        "source_refs": update.get("source_refs") or document.get("source_refs") or [],
        "review_decision": decision,
        "reviewed_at": now_iso(),
        "review_note": note,
        "updates": [update],
    }
    atomic_yaml(destination / f"{path.stem}-{update['proposal_id']}.yaml", archive)
    document["updates"].pop(index)
    if document["updates"]:
        atomic_yaml(path, document)
    else:
        path.unlink()


def idempotency_records() -> dict:
    if not REVIEW_IDEMPOTENCY.exists():
        return {}
    try:
        value = json.loads(REVIEW_IDEMPOTENCY.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def accept(proposal_id: str, revision: object, idempotency_key: str) -> dict:
    if not idempotency_key or len(idempotency_key) > 200:
        raise ReviewError("an idempotency key is required")
    with review_lock():
        records = idempotency_records()
        if idempotency_key in records:
            return records[idempotency_key]
        path, document, index, update = find_item(proposal_id)
        check_revision(update, revision)
        single = {"source_refs": document.get("source_refs") or [], "updates": [update]}
        problems = validate(single, load_schema())
        if problems:
            raise ValidationFailure(problems)

        schema = load_schema()
        category = update["category"]
        tracker_path = REPO_ROOT / schema["categories"][category]["tracker_file"]
        backup = tracker_path.read_bytes() if tracker_path.exists() else None
        fields = dict(update.get("fields") or {})
        if update.get("action", "add") == "update":
            fields[id_column(category, schema)] = update["id"]
            if category == "risk" and ({"Probability", "Impact"} & set(fields)):
                existing = current_row(update, schema) or {}
                for input_name in ("Probability", "Impact"):
                    if fields.get(input_name) in (None, "") and existing.get(input_name) not in (None, ""):
                        fields[input_name] = existing[input_name]
        refs = update.get("source_refs") or document.get("source_refs") or []
        fields["Source Refs"] = schema["list_delimiter"].join(refs)
        try:
            row_id = upsert_row(category, fields, schema)
            sync = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("sync.py"))],
                capture_output=True, text=True, cwd=REPO_ROOT,
            )
            if sync.returncode:
                raise ReviewError(sync.stderr.strip() or sync.stdout.strip() or "sync failed")
        except Exception:
            if backup is None:
                tracker_path.unlink(missing_ok=True)
            else:
                tracker_path.write_bytes(backup)
            raise

        result = {"proposal_id": proposal_id, "tracker_id": row_id,
                  "category": category, "decision": "accepted"}
        remove_and_archive(path, document, index, update, APPLIED_UPDATES_DIR, "accepted")
        append_history("accept", update, {"tracker_id": row_id})
        records[idempotency_key] = result
        atomic_write_text(REVIEW_IDEMPOTENCY, json.dumps(records, indent=2, sort_keys=True))
        return result


def reject(proposal_id: str, revision: object, reason: str = "") -> dict:
    with review_lock():
        path, document, index, update = find_item(proposal_id)
        check_revision(update, revision)
        remove_and_archive(path, document, index, update, REJECTED_UPDATES_DIR, "rejected", reason)
        append_history("reject", update, {"reason": reason})
        return {"proposal_id": proposal_id, "decision": "rejected"}


def load_queue() -> dict:
    if not AI_REVIEW_QUEUE.exists():
        return {"sequence": 0, "items": []}
    value = yaml.safe_load(AI_REVIEW_QUEUE.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {"sequence": 0, "items": []}


def flag(proposal_id: str, revision: object, note: str = "") -> dict:
    with review_lock():
        path, document, _index, update = find_item(proposal_id)
        check_revision(update, revision)
        update["revision"] += 1
        update["review"] = {"state": "flagged", "clarification_note": note,
                            "flagged_at": now_iso()}
        atomic_yaml(path, document)
        queue = load_queue()
        sequence = int(queue.get("sequence", 0)) + 1
        item = {"sequence": sequence, "proposal_id": proposal_id,
                "category": update.get("category"), "note": note,
                "timestamp": now_iso(), "revision": update["revision"]}
        queue["sequence"] = sequence
        queue.setdefault("items", []).append(item)
        atomic_yaml(AI_REVIEW_QUEUE, queue)
        append_history("flag", update, {"clarification_note": note, "sequence": sequence})
        return item


def queue_after(sequence: int) -> dict:
    with review_lock():
        queue = load_queue()
        items = [item for item in queue.get("items", [])
                 if int(item.get("sequence", 0)) > sequence]
        return {"sequence": int(queue.get("sequence", 0)), "items": items}
