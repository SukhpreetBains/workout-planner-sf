"""Transactional item-level review operations for proposed tracker updates."""

from __future__ import annotations

import errno
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
from trackers import (
    delete_row,
    format_relationships,
    id_column,
    is_relationships,
    is_workspace_timeout,
    parse_relationships,
    read_rows,
    upsert_row,
)
from validate_updates import validate

USER_SUBMITTED_SOURCE = "User Submitted"


class ReviewError(RuntimeError):
    status = 400


ONEDRIVE_RETRY_MESSAGE = (
    "OneDrive is temporarily delaying access to a workspace file. "
    "Wait for OneDrive to finish syncing, then retry this review action."
)


def workspace_timeout_error(error: BaseException) -> ReviewError:
    return ReviewError(ONEDRIVE_RETRY_MESSAGE)


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


def pending_link_ids() -> dict[str, set[str]]:
    """Return the proposal IDs that may temporarily occupy relationship fields."""
    values: dict[str, set[str]] = {}
    for path in proposal_files():
        document = load_yaml(path)
        if upgrade_document(path, document):
            atomic_yaml(path, document)
        for update in document["updates"]:
            category = str(update.get("category", ""))
            proposal_id = str(update.get("proposal_id", ""))
            if category and proposal_id:
                values.setdefault(category, set()).add(proposal_id)
    return values


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


def display_label(category: str, fields: dict, schema: dict) -> str:
    """Return one consistent human label for tracker rows and proposals."""
    for value in (fields.get("Name"), fields.get(id_column(category, schema))):
        if str(value or "").strip():
            return str(value).strip()
    return "Untitled"


def category_label(category: str, schema: dict) -> str:
    return schema["categories"].get(category, {}).get("label") or category.replace("_", " ").title()


def catalog(schema: dict) -> dict:
    """The configurable vocabulary the review interface renders."""
    return {
        "groups": [{"id": key, "label": group["label"], "definition": group["definition"]}
                   for key, group in schema["groups"].items()],
        "categories": [{"id": key, "label": definition["label"], "group": definition["group"],
                        "definition": definition["definition"],
                        "field_schema": definition.get("columns", [])}
                       for key, definition in schema["categories"].items()],
        "relationships": [{"id": key, "label": meaning["label"],
                           "inverse_label": meaning["inverse_label"],
                           "definition": meaning["definition"]}
                          for key, meaning in schema["relationships"].items()],
    }


def archived_counts(directory: Path, excluded_tracker_ids: set[tuple[str, str]] | None = None) -> dict[str, int]:
    counts: dict[str, int] = {}
    excluded_tracker_ids = excluded_tracker_ids or set()
    if not directory.exists():
        return counts
    for path in sorted(directory.glob("*.y*ml")):
        try:
            document = load_yaml(path)
        except (OSError, ReviewError, yaml.YAMLError):
            continue
        for update in document["updates"]:
            category = str(update.get("category", ""))
            tracker_id = str(document.get("tracker_id", ""))
            if category and (category, tracker_id) not in excluded_tracker_ids:
                counts[category] = counts.get(category, 0) + 1
    return counts


def rejected_accepted_tracker_ids() -> set[tuple[str, str]]:
    values: set[tuple[str, str]] = set()
    if not REJECTED_UPDATES_DIR.exists():
        return values
    for path in REJECTED_UPDATES_DIR.glob("*.y*ml"):
        try:
            document = load_yaml(path)
        except (OSError, ReviewError, yaml.YAMLError):
            continue
        category = str(document.get("category", ""))
        tracker_id = str(document.get("tracker_id", ""))
        if category and tracker_id:
            values.add((category, tracker_id))
    return values


def returned_accepted_tracker_ids() -> set[tuple[str, str]]:
    """Return accepted rows that were restored to the review inbox."""
    values: set[tuple[str, str]] = set()
    if not APPLIED_UPDATES_DIR.exists():
        return values
    for path in APPLIED_UPDATES_DIR.glob("*.y*ml"):
        try:
            document = load_yaml(path)
        except (OSError, ReviewError, yaml.YAMLError):
            continue
        if document.get("review_decision") != "returned_to_pending":
            continue
        category = str(document.get("category", ""))
        tracker_id = str(document.get("tracker_id", ""))
        if category and tracker_id:
            values.add((category, tracker_id))
    return values


def progress_summary(cards: list[dict], schema: dict) -> dict:
    inactive_accepted = rejected_accepted_tracker_ids() | returned_accepted_tracker_ids()
    accepted_by_category = archived_counts(APPLIED_UPDATES_DIR, inactive_accepted)
    rejected_by_category = archived_counts(REJECTED_UPDATES_DIR)
    categories = {}
    for category in schema["categories"]:
        category_cards = [card for card in cards if card["category"] == category]
        pending = len(category_cards)
        accepted = accepted_by_category.get(category, 0)
        rejected = rejected_by_category.get(category, 0)
        completed = accepted + rejected
        categories[category] = {
            "pending": pending,
            "accepted": accepted,
            "rejected": rejected,
            "flagged": sum(
                card.get("review", {}).get("state") == "flagged"
                for card in category_cards
            ),
            "completed": completed,
            "total": pending + completed,
        }
    accepted = sum(accepted_by_category.values())
    rejected = sum(rejected_by_category.values())
    pending = len(cards)
    return {
        "pending": pending,
        "accepted": accepted,
        "rejected": rejected,
        "flagged": sum(
            card.get("review", {}).get("state") == "flagged" for card in cards
        ),
        "completed": accepted + rejected,
        "total": pending + accepted + rejected,
        "categories": categories,
    }


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
                    "category_label": category_label(category, schema),
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
    return {
        "cards": cards,
        "counts": counts,
        **catalog(schema),
        "remaining": len(cards),
        "progress": progress_summary(cards, schema),
    }


def create(category: str, source_ref: str) -> dict:
    """Create a human-authored pending proposal without writing a tracker row."""
    schema = load_schema()
    if category not in schema["categories"]:
        raise ReviewError("unknown tracker category")
    source_ref = str(source_ref).strip()
    if not source_ref:
        raise ReviewError("a workspace source reference is required")
    if source_ref != USER_SUBMITTED_SOURCE:
        try:
            source_path = (REPO_ROOT / source_ref).resolve()
            source_path.relative_to(REPO_ROOT / "workspace")
        except ValueError as exc:
            raise ReviewError("source reference must be inside the workspace") from exc
        if not source_path.is_file():
            raise ReviewError("source reference must identify an existing workspace file")

    proposal_id = str(uuid.uuid4())
    update = {
        "proposal_id": proposal_id,
        "revision": 1,
        "category": category,
        "action": "add",
        "fields": {},
        "source_refs": [source_ref],
        "evidence": [{"source_ref": source_ref, "excerpt": "Manually created in review inbox."}],
        "review": {"state": "pending"},
    }
    with review_lock():
        path = PROPOSED_UPDATES_DIR / f"manual-{proposal_id}.yaml"
        atomic_yaml(path, {"source_refs": [source_ref], "updates": [update]})
        append_history("create", update, {"source_ref": source_ref})
    return {"proposal_id": proposal_id}


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
                            load_schema(), pending_link_ids())
        update["fields"] = candidate["fields"]
        update["revision"] += 1
        atomic_yaml(path, document)
        append_history("edit", update, {"valid": not problems, "validation": problems})
        return {"proposal_id": proposal_id, "revision": update["revision"], "validation": problems}


def remove_and_archive(path: Path, document: dict, index: int, update: dict,
                       destination: Path, decision: str, note: str = "", tracker_id: str = "") -> None:
    destination.mkdir(parents=True, exist_ok=True)
    archive = {
        "source_refs": update.get("source_refs") or document.get("source_refs") or [],
        "review_decision": decision,
        "reviewed_at": now_iso(),
        "review_note": note,
        "updates": [update],
    }
    if tracker_id:
        archive["tracker_id"] = tracker_id
    atomic_yaml(destination / f"{path.stem}-{update['proposal_id']}.yaml", archive)
    document["updates"].pop(index)
    if document["updates"]:
        atomic_yaml(path, document)
    else:
        path.unlink()


def references(value: object, target: str) -> bool:
    return any(linked == target for _meaning, linked in parse_relationships(value))


def replace_relationship_target(value: object, old: str, new: str) -> str:
    """Point relationships at a new ID, or drop them when there is none."""
    return format_relationships([
        (meaning, new if linked == old else linked)
        for meaning, linked in parse_relationships(value)
        if linked != old or new
    ])


def resolve_links(old: str, new: str, schema: dict) -> list[str]:
    """Replace a proposal ID in every relationship field, or remove it on rejection."""
    affected_accepted: list[str] = []
    for path in proposal_files():
        document = load_yaml(path)
        changed = False
        for update in document["updates"]:
            update_changed = False
            definition = schema["categories"].get(update.get("category"), {})
            fields = update.get("fields") or {}
            for column in definition.get("columns", []):
                if not is_relationships(column):
                    continue
                name = column["name"]
                if references(fields.get(name), old):
                    fields[name] = replace_relationship_target(fields.get(name), old, new)
                    changed = True
                    update_changed = True
            update["fields"] = fields
            if update_changed:
                update["revision"] += 1
        if changed:
            atomic_yaml(path, document)

    for category, definition in schema["categories"].items():
        for row in read_rows(category, schema):
            changed = False
            for column in definition.get("columns", []):
                if not is_relationships(column):
                    continue
                name = column["name"]
                if references(row.get(name), old):
                    row[name] = replace_relationship_target(row.get(name), old, new)
                    changed = True
            if changed:
                row[id_column(category, schema)] = row.get(id_column(category, schema), "")
                affected_accepted.append(display_label(category, row, schema))
                upsert_row(category, row, schema)
    return affected_accepted


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
        problems = validate(single, load_schema(), pending_link_ids())
        if problems:
            raise ValidationFailure(problems)

        schema = load_schema()
        category = update["category"]
        tracker_path = REPO_ROOT / schema["categories"][category]["tracker_file"]
        try:
            backup = tracker_path.read_bytes() if tracker_path.exists() else None
        except OSError as error:
            if is_workspace_timeout(error):
                raise workspace_timeout_error(error) from error
            raise
        fields = dict(update.get("fields") or {})
        if update.get("action", "add") == "update":
            fields[id_column(category, schema)] = update["id"]
            scored = any(column.get("computed") == "risk_score"
                         for column in schema["categories"][category]["columns"])
            if scored and ({"Probability", "Impact"} & set(fields)):
                existing = current_row(update, schema) or {}
                for input_name in ("Probability", "Impact"):
                    if fields.get(input_name) in (None, "") and existing.get(input_name) not in (None, ""):
                        fields[input_name] = existing[input_name]
        refs = update.get("source_refs") or document.get("source_refs") or []
        fields["Source Refs"] = schema["list_delimiter"].join(refs)
        try:
            row_id = upsert_row(category, fields, schema)
            resolve_links(proposal_id, row_id, schema)
            previous_tracker_id = str(document.get("accepted_tracker_id", ""))
            if previous_tracker_id:
                resolve_links(previous_tracker_id, row_id, schema)
            path, document, index, update = find_item(proposal_id)
            sync = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("sync.py"))],
                capture_output=True, text=True, cwd=REPO_ROOT,
            )
            if sync.returncode:
                raise ReviewError(sync.stderr.strip() or sync.stdout.strip() or "sync failed")
        except Exception as error:
            try:
                if backup is None:
                    tracker_path.unlink(missing_ok=True)
                else:
                    tracker_path.write_bytes(backup)
            except OSError as rollback_error:
                if is_workspace_timeout(rollback_error):
                    raise workspace_timeout_error(rollback_error) from rollback_error
                raise
            if is_workspace_timeout(error):
                raise workspace_timeout_error(error) from error
            raise

        result = {"proposal_id": proposal_id, "tracker_id": row_id,
                  "category": category, "decision": "accepted"}
        remove_and_archive(path, document, index, update, APPLIED_UPDATES_DIR, "accepted", tracker_id=row_id)
        append_history("accept", update, {"tracker_id": row_id})
        records[idempotency_key] = result
        atomic_write_text(REVIEW_IDEMPOTENCY, json.dumps(records, indent=2, sort_keys=True))
        return result


def reject(proposal_id: str, revision: object, reason: str = "") -> dict:
    with review_lock():
        path, document, index, update = find_item(proposal_id)
        check_revision(update, revision)
        affected_accepted = resolve_links(proposal_id, "", load_schema())
        path, document, index, update = find_item(proposal_id)
        remove_and_archive(path, document, index, update, REJECTED_UPDATES_DIR, "rejected", reason)
        append_history("reject", update, {"reason": reason})
        result = {"proposal_id": proposal_id, "decision": "rejected"}
        if affected_accepted:
            result["warning"] = ("Rejected. Removed links from accepted item"
                                 f"{'s' if len(affected_accepted) != 1 else ''}: "
                                 f"{', '.join(affected_accepted)}.")
        return result


def applied_evidence_index() -> dict[str, object]:
    """Read applied archives once and retain every update, including batch files."""
    by_tracker: dict[tuple[str, str], tuple[Path, dict, dict]] = {}
    legacy: dict[str, list[tuple[Path, dict, dict]]] = {}
    for path in APPLIED_UPDATES_DIR.glob("*.y*ml"):
        try:
            document = load_yaml(path)
        except (OSError, ReviewError, yaml.YAMLError):
            continue
        tracker_id = str(document.get("tracker_id", ""))
        for update in document["updates"]:
            category = str(update.get("category", ""))
            if not category:
                continue
            if tracker_id:
                by_tracker[(category, tracker_id)] = (path, document, update)
            legacy.setdefault(category, []).append((path, document, update))
    return {"by_tracker": by_tracker, "legacy": legacy}


def archived_update_for_accepted(category: str, tracker_id: str, fields: dict,
                                 evidence_index: dict[str, object] | None = None) -> tuple[Path, dict, dict] | None:
    """Locate the one archived proposal that produced an accepted tracker row."""
    evidence_index = evidence_index or applied_evidence_index()
    by_tracker = evidence_index["by_tracker"]
    legacy = evidence_index["legacy"]
    update = by_tracker.get((category, tracker_id))
    if update:
        return update
    candidates: list[tuple[int, Path, dict, dict]] = []
    for path, document, update in legacy.get(category, []):
        if update.get("id") == tracker_id:
            return path, document, update
        # Archives created before tracker IDs were recorded can still be matched
        # to their row through the proposal's identifying field values.
        proposal_fields = update.get("fields") or {}
        score = sum(
            str(value).strip().casefold() == str(fields.get(name, "")).strip().casefold()
            for name, value in proposal_fields.items()
            if value not in (None, "") and fields.get(name) not in (None, "")
        )
        if score:
            candidates.append((score, path, document, update))
    if candidates:
        candidates.sort(key=lambda candidate: candidate[0], reverse=True)
        if len(candidates) == 1 or candidates[0][0] > candidates[1][0]:
            _score, path, document, update = candidates[0]
            return path, document, update
    return None


def accepted_evidence(category: str, tracker_id: str, fields: dict, source_refs: list[str],
                      evidence_index: dict[str, object] | None = None) -> list[dict]:
    """Return the selected accepted value's proposal evidence, with a legacy fallback."""
    archived = archived_update_for_accepted(category, tracker_id, fields, evidence_index)
    if archived:
        _path, _document, update = archived
        return update.get("evidence") or [
            {"source_ref": ref, "excerpt": ""} for ref in (update.get("source_refs") or source_refs)
        ]
    return [{"source_ref": ref, "excerpt": "No excerpt was captured for this older approval."} for ref in source_refs]


def reject_accepted(category: str, tracker_id: str, reason: str = "") -> dict:
    """Remove an accepted tracker row and record its later rejection."""
    schema = load_schema()
    if category not in schema["categories"]:
        raise ReviewError("unknown tracker category")
    with review_lock():
        identifier = id_column(category, schema)
        row = next((item for item in read_rows(category, schema) if item.get(identifier) == tracker_id), None)
        if row is None:
            raise NotFound(f"{category} row {tracker_id} was not found")
        source_refs = [ref.strip() for ref in str(row.get("Source Refs", "")).split(schema["list_delimiter"]) if ref.strip()]
        evidence = accepted_evidence(category, tracker_id, row, source_refs)
        archived = archived_update_for_accepted(category, tracker_id, row)
        if archived:
            archive_path, archive_document, _update = archived
            if not archive_document.get("tracker_id"):
                archive_document["tracker_id"] = tracker_id
                atomic_yaml(archive_path, archive_document)
        delete_row(category, tracker_id, schema)
        resolve_links(tracker_id, "", schema)
        sync = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("sync.py")), "--trackers-only"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        if sync.returncode:
            raise ReviewError(sync.stderr.strip() or sync.stdout.strip() or "sync failed")
        archive = {
            "category": category,
            "tracker_id": tracker_id,
            "source_refs": source_refs,
            "review_decision": "rejected_after_acceptance",
            "reviewed_at": now_iso(),
            "review_note": reason,
            "updates": [{"proposal_id": f"accepted-{category}-{tracker_id}", "revision": 1,
                         "category": category, "action": "delete", "id": tracker_id,
                         "fields": row, "source_refs": source_refs, "evidence": evidence}],
        }
        atomic_yaml(REJECTED_UPDATES_DIR / f"accepted-{category}-{tracker_id}.yaml", archive)
        append_history("reject-accepted", archive["updates"][0], {"tracker_id": tracker_id, "reason": reason})
        return {"category": category, "tracker_id": tracker_id, "decision": "rejected"}


def proposal_fields_from_row(category: str, row: dict, schema: dict) -> dict:
    """Keep editable, non-computed fields when returning an accepted row to pending."""
    return {
        column["name"]: row.get(column["name"], "")
        for column in schema["categories"][category].get("columns", [])
        if not column.get("computed") and column["name"] in row
    }


def move_accepted_to_pending(category: str, tracker_id: str) -> dict:
    """Restore an accepted tracker row as an editable pending proposal."""
    schema = load_schema()
    if category not in schema["categories"]:
        raise ReviewError("unknown tracker category")
    with review_lock():
        identifier = id_column(category, schema)
        row = next((item for item in read_rows(category, schema) if item.get(identifier) == tracker_id), None)
        if row is None:
            raise NotFound(f"{category} row {tracker_id} was not found")
        source_refs = [ref.strip() for ref in str(row.get("Source Refs", "")).split(schema["list_delimiter"]) if ref.strip()]
        evidence = accepted_evidence(category, tracker_id, row, source_refs)
        proposal_id = str(uuid.uuid4())
        update = {
            "proposal_id": proposal_id,
            "revision": 1,
            "category": category,
            "action": "add",
            "fields": proposal_fields_from_row(category, row, schema),
            "source_refs": source_refs,
            "evidence": evidence,
            "review": {"state": "pending"},
        }
        tracker_path = REPO_ROOT / schema["categories"][category]["tracker_file"]
        backup = tracker_path.read_bytes() if tracker_path.exists() else None
        pending_path = PROPOSED_UPDATES_DIR / f"returned-{category}-{proposal_id}.yaml"
        try:
            delete_row(category, tracker_id, schema)
            sync = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("sync.py")), "--trackers-only"],
                capture_output=True, text=True, cwd=REPO_ROOT,
            )
            if sync.returncode:
                raise ReviewError(sync.stderr.strip() or sync.stdout.strip() or "sync failed")
            atomic_yaml(pending_path, {"source_refs": source_refs, "accepted_tracker_id": tracker_id,
                                       "updates": [update]})
            archived = archived_update_for_accepted(category, tracker_id, row)
            if archived:
                archive_path, archive_document, _archived_update = archived
                archive_document["category"] = category
                archive_document["tracker_id"] = tracker_id
                archive_document["review_decision"] = "returned_to_pending"
                archive_document["returned_proposal_id"] = proposal_id
                atomic_yaml(archive_path, archive_document)
            else:
                atomic_yaml(APPLIED_UPDATES_DIR / f"returned-{category}-{tracker_id}.yaml", {
                    "category": category, "tracker_id": tracker_id,
                    "review_decision": "returned_to_pending", "reviewed_at": now_iso(), "updates": [],
                })
        except Exception:
            pending_path.unlink(missing_ok=True)
            if backup is None:
                tracker_path.unlink(missing_ok=True)
            else:
                tracker_path.write_bytes(backup)
            raise
        append_history("return-to-pending", update, {"tracker_id": tracker_id})
        return {"proposal_id": proposal_id, "category": category, "decision": "pending"}


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
