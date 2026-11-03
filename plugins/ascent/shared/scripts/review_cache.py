"""Persistent local working copy for the review inbox.

The OneDrive project remains canonical. Review requests use a local mirror and
this module reconciles review-owned files to OneDrive in the background.
"""

from __future__ import annotations

import hashlib
import getpass
import json
import os
import shutil
import tempfile
import threading
import time
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree
from datetime import datetime, timezone
from pathlib import Path
from pathlib import PurePosixPath

SYNC_INTERVAL = 300
EDITOR_LEDGER = "workspace/.system/review-file-editors.json"
SKIP = {
    "workspace/.system/review-server.json",
    "workspace/.system/review-server.log",
    "workspace/.system/review.lock",
    "workspace/.system/.venv-path",
}
# Snapshots kept for recovery. Review never reads them, and OneDrive often keeps
# them online-only, where reading one can stall the first local copy.
SKIP_DIRS = {"workspace/.system/backups"}
WRITE_PREFIXES = (
    "workspace/trackers/",
    "workspace/.system/proposed-updates/",
    "workspace/.system/applied-updates/",
    "workspace/.system/rejected-updates/",
    "workspace/.system/tracker-copies/",
    "workspace/.system/search/",
)
WRITE_FILES = {
    "workspace/.system/ai-review-queue.yaml",
    "workspace/.system/review-history.jsonl",
    "workspace/.system/review-idempotency.json",
    "workspace/.system/sync-state.json",
}


def cache_dir(project_root: Path) -> Path:
    identity = hashlib.sha256(str(project_root.resolve()).encode()).hexdigest()[:20]
    return Path.home() / ".ascent" / "review-cache" / identity


def review_owned(relative: str) -> bool:
    return relative in WRITE_FILES or relative.startswith(WRITE_PREFIXES)


def files(root: Path, review_only: bool = False) -> dict[str, Path]:
    workspace = root / "workspace"
    if not workspace.is_dir():
        raise FileNotFoundError(f"workspace is unavailable: {workspace}")
    result = {}
    def fail(error: OSError) -> None:
        raise error
    for directory, names, filenames in os.walk(workspace, onerror=fail):
        names[:] = [name for name in names if not (Path(directory) / name).is_symlink()
                    and (Path(directory) / name).relative_to(root).as_posix() not in SKIP_DIRS]
        for name in filenames:
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if (relative not in SKIP and (not review_only or review_owned(relative))
                    and path.is_file() and not path.is_symlink()):
                result[relative] = path
    return result


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def snapshot(root: Path) -> dict[str, str]:
    return {name: digest(path) for name, path in files(root, review_only=True).items()}


def file_stamps(root: Path) -> dict[str, tuple[int, int]]:
    """Cheap before-and-after check for files touched by one review action."""
    return {name: (path.stat().st_mtime_ns, path.stat().st_size)
            for name, path in files(root, review_only=True).items()}


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with source.open("rb") as input_file, os.fdopen(descriptor, "wb") as output:
            shutil.copyfileobj(input_file, output)
            output.flush()
            os.fsync(output.fileno())
        source_stat = source.stat()
        os.utime(temporary, ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns))
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def current_editor() -> str:
    """Use the signed-in person's full OS display name when available."""
    try:
        import pwd
        name = pwd.getpwuid(os.getuid()).pw_gecos.split(",", 1)[0].strip()
        if name:
            return name
    except (ImportError, KeyError, OSError, AttributeError):
        pass
    return getpass.getuser()


def read_editors(root: Path) -> dict[str, dict]:
    try:
        value = json.loads((root / EDITOR_LEDGER).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        return {}
    entries = value.get("files", {}) if isinstance(value, dict) else {}
    return entries if isinstance(entries, dict) else {}


def write_editors(root: Path, updates: dict[str, dict | None]) -> None:
    entries = read_editors(root)
    for relative, entry in updates.items():
        if entry:
            entries[relative] = entry
        else:
            entries.pop(relative, None)
    path = root / EDITOR_LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".review-file-editors.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump({"files": entries}, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class SyncConflictError(RuntimeError):
    """A file changed after the reviewer opened the sync comparison."""


def version(path: Path, editor: dict | None = None) -> dict:
    if not path.is_file():
        return {"exists": False, "fingerprint": None, "modified_at": None,
                "modified_ns": None, "modified_by": "Unknown"}
    stat = path.stat()
    modified_by = "Unknown"
    if path.suffix.lower() == ".xlsx":
        try:
            with ZipFile(path) as workbook:
                core = ElementTree.fromstring(workbook.read("docProps/core.xml"))
                modified_by = next((element.text.strip() for element in core.iter()
                                    if element.tag.endswith("}lastModifiedBy") and element.text
                                    and element.text.strip()), "Unknown")
        except (BadZipFile, KeyError, OSError, ElementTree.ParseError):
            pass
    fingerprint = digest(path)
    modified_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
    if isinstance(editor, dict) and editor.get("fingerprint") == fingerprint:
        modified_by = str(editor.get("modified_by") or modified_by)
        modified_at = str(editor.get("modified_at") or modified_at)
    return {"exists": True, "fingerprint": fingerprint,
            "modified_at": modified_at,
            "modified_ns": stat.st_mtime_ns, "modified_by": modified_by}


def safe_review_path(relative: str) -> bool:
    parts = PurePosixPath(relative).parts
    return bool(parts) and "." not in parts and ".." not in parts and review_owned(relative)


def same_workbook_content(left: Path, right: Path) -> bool:
    """Compare Excel content while ignoring OneDrive's package metadata."""
    def payload(path: Path) -> dict[str, str]:
        with ZipFile(path) as workbook:
            result = {
                name: hashlib.sha256(workbook.read(name)).hexdigest()
                for name in workbook.namelist()
                if name.startswith("xl/") and name != "xl/_rels/workbook.xml.rels"
            }
            relationships = ElementTree.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
            essential = sorted((item.get("Id"), item.get("Type"), item.get("Target"),
                                item.get("TargetMode")) for item in relationships
                               if not item.get("Type", "").endswith("/customXml"))
            result["xl/_rels/workbook.xml.rels"] = hashlib.sha256(repr(essential).encode()).hexdigest()
            return result
    return payload(left) == payload(right)


class ReviewCache:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.directory = cache_dir(self.project_root)
        self.local_root = self.directory / "project"
        self.manifest_path = self.directory / "manifest.json"
        self.lock = threading.RLock()
        self.work_lock = threading.RLock()
        self.sync_lock = threading.Lock()
        self.wake = threading.Event()
        self.stop_event = threading.Event()
        self.baseline: dict[str, str] = {}
        self.editors: dict[str, dict] = {}
        self.status = {"state": "starting", "pending": 0, "conflicts": [],
                       "last_success": None, "error": None}
        self.thread: threading.Thread | None = None

    def prepare(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        os.chmod(self.directory, 0o700)
        if self.manifest_path.is_file() and (self.local_root / "workspace").is_dir():
            value = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if value.get("project_root") != str(self.project_root):
                raise RuntimeError("review cache belongs to another project")
            self.baseline = {name: value for name, value in value.get("files", {}).items()
                             if review_owned(name)}
            self.editors = {name: editor for name, editor in value.get("editors", {}).items()
                            if review_owned(name) and isinstance(editor, dict)}
            for name, editor in read_editors(self.project_root).items():
                if (review_owned(name) and name not in self.editors
                        and isinstance(editor, dict)
                        and editor.get("fingerprint") == self.baseline.get(name)):
                    self.editors[name] = editor
            self.status.update(value.get("status", {}))
            self.status["state"] = "local"
            return
        if self.local_root.exists():
            raise RuntimeError("incomplete review cache needs inspection before reuse")
        staging = self.directory / "initial-copy"
        if staging.exists():
            shutil.rmtree(staging)
        try:
            for relative, source in files(self.project_root).items():
                atomic_copy(source, staging / relative)
            baseline = snapshot(staging)
            os.replace(staging, self.local_root)
            self.baseline = baseline
            self.editors = {name: editor for name, editor in read_editors(self.project_root).items()
                            if review_owned(name) and isinstance(editor, dict)
                            and editor.get("fingerprint") == baseline.get(name)}
            self.status.update({"state": "synced", "last_success": now()})
            self._save_manifest()
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def _save_manifest(self) -> None:
        with self.lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=".manifest.", dir=self.directory)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    json.dump({"project_root": str(self.project_root), "files": self.baseline,
                               "editors": self.editors, "status": self.status}, handle, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self.manifest_path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def status_json(self) -> dict:
        with self.lock:
            return dict(self.status, conflicts=list(self.status["conflicts"]))

    def request_sync(self) -> None:
        self.wake.set()

    def sync_now(self) -> dict:
        """Complete one sync attempt and return its final status to the caller."""
        try:
            self.sync_once()
        except Exception as error:
            with self.lock:
                self.status.update({"state": "offline", "error": str(error)})
                self._save_manifest()
        return self.status_json()

    def sync_preview(self) -> dict:
        """Compare differing review files without publishing either version."""
        remote = snapshot(self.project_root)
        with self.work_lock:
            local = snapshot(self.local_root)
            baseline = dict(self.baseline)
            local_editors = dict(self.editors)
        cloud_editors = read_editors(self.project_root)
        items = []
        for relative in sorted(set(remote) | set(local)):
            if not safe_review_path(relative) or local.get(relative) == remote.get(relative):
                continue
            local_path, cloud_path = self.local_root / relative, self.project_root / relative
            if (relative.endswith(".xlsx") and local_path.is_file() and cloud_path.is_file()
                    and same_workbook_content(local_path, cloud_path)):
                continue
            local_version = version(local_path, local_editors.get(relative))
            cloud_version = version(cloud_path, cloud_editors.get(relative))
            items.append({"path": relative, "local": local_version, "cloud": cloud_version,
                          "local_changed": local.get(relative) != baseline.get(relative),
                          "cloud_changed": remote.get(relative) != baseline.get(relative)})
        return {"items": items}

    def overwrite_all(self, requested: list[dict]) -> dict:
        """Publish every available local difference after one complete preflight."""
        if not isinstance(requested, list):
            raise ValueError("file comparisons are required")
        with self.sync_lock:
            current = self.sync_preview()["items"]
            observed = {item["path"]: item for item in current}
            available = {name: item for name, item in observed.items() if item["local"]["exists"]}
            supplied = {item.get("path"): item for item in requested if isinstance(item, dict)}
            if set(supplied) != set(observed) or len(supplied) != len(requested):
                raise SyncConflictError("The file list changed. Reopen Sync now to compare again.")
            for relative, item in supplied.items():
                if not safe_review_path(relative):
                    raise ValueError("invalid review file path")
                for side in ("local", "cloud"):
                    expected, actual = item.get(side), observed[relative][side]
                    if not isinstance(expected, dict) or any(
                        expected.get(key) != actual[key] for key in ("fingerprint", "modified_ns")
                    ):
                        raise SyncConflictError("A file changed. Reopen Sync now to compare again.")
                for root in (self.local_root, self.project_root):
                    path = root / relative
                    try:
                        path.resolve().relative_to(root.resolve())
                    except ValueError as exc:
                        raise ValueError("review file path leaves the workspace") from exc
                    if path.is_symlink():
                        raise ValueError("review file path cannot be a link")
            if not available:
                return {"updated": []}

            staging = Path(tempfile.mkdtemp(prefix="manual-batch-", dir=self.directory))
            published = []
            try:
                with self.work_lock:
                    local_editors = dict(self.editors)
                    for relative, item in available.items():
                        source = self.local_root / relative
                        if any(version(source)[key] != item["local"][key]
                               for key in ("fingerprint", "modified_ns")):
                            raise SyncConflictError("A local file changed. Reopen Sync now to compare again.")
                        atomic_copy(source, staging / "local" / relative)
                        if digest(staging / "local" / relative) != item["local"]["fingerprint"]:
                            raise SyncConflictError("A local file changed during copy. Reopen Sync now.")
                for relative, item in available.items():
                    cloud_path = self.project_root / relative
                    if item["cloud"]["exists"]:
                        atomic_copy(cloud_path, staging / "cloud" / relative)
                    if any(version(cloud_path)[key] != item["cloud"][key]
                           for key in ("fingerprint", "modified_ns")):
                        raise SyncConflictError("A cloud file changed. Reopen Sync now to compare again.")
                for relative, item in available.items():
                    if any(version(self.local_root / relative)[key] != item["local"][key]
                           for key in ("fingerprint", "modified_ns")):
                        raise SyncConflictError("A local file changed. Reopen Sync now to compare again.")
                    if any(version(self.project_root / relative)[key] != item["cloud"][key]
                           for key in ("fingerprint", "modified_ns")):
                        raise SyncConflictError("A cloud file changed. Reopen Sync now to compare again.")
                for relative, item in available.items():
                    destination = self.project_root / relative
                    if any(version(destination)[key] != item["cloud"][key]
                           for key in ("fingerprint", "modified_ns")):
                        raise SyncConflictError("A cloud file changed. Reopen Sync now to compare again.")
                    atomic_copy(staging / "local" / relative, destination)
                    published.append(relative)
                    if digest(destination) != item["local"]["fingerprint"]:
                        raise OSError(f"Cloud copy did not match the local version: {relative}")
                for relative, item in available.items():
                    if any(version(self.local_root / relative)[key] != item["local"][key]
                           for key in ("fingerprint", "modified_ns")):
                        raise SyncConflictError("A local file changed. Reopen Sync now to compare again.")
                    if digest(self.project_root / relative) != item["local"]["fingerprint"]:
                        raise SyncConflictError("A cloud file changed. Reopen Sync now to compare again.")
                editor_updates = {}
                for relative, item in available.items():
                    editor = local_editors.get(relative)
                    editor_updates[relative] = editor if isinstance(editor, dict) and editor.get(
                        "fingerprint") == item["local"]["fingerprint"] else {
                            "fingerprint": item["local"]["fingerprint"],
                        "modified_at": item["local"]["modified_at"], "modified_by": "Unknown",
                        }
                write_editors(self.project_root, editor_updates)
            except Exception:
                for relative in reversed(published):
                    backup = staging / "cloud" / relative
                    destination = self.project_root / relative
                    if backup.is_file():
                        atomic_copy(backup, destination)
                    else:
                        destination.unlink(missing_ok=True)
                raise
            finally:
                shutil.rmtree(staging, ignore_errors=True)
            with self.work_lock:
                for relative, item in available.items():
                    self.baseline[relative] = item["local"]["fingerprint"]
                self.status.update({"state": "local", "error": None, "last_success": now()})
                self._save_manifest()
        self.request_sync()
        return {"updated": sorted(available)}

    def mark_local_change(self, changed: set[str] | None = None) -> None:
        with self.lock:
            for relative in changed or set():
                if not review_owned(relative):
                    continue
                file_version = version(self.local_root / relative)
                if file_version["exists"]:
                    self.editors[relative] = {
                        "fingerprint": file_version["fingerprint"],
                        "modified_at": file_version["modified_at"],
                        "modified_by": current_editor(),
                    }
                else:
                    self.editors.pop(relative, None)
            if self.status["state"] not in ("conflict", "offline"):
                self.status["state"] = "local"
            self.status["pending"] = max(1, self.status["pending"])
            self._save_manifest()

    def publish_cloud_editors(self) -> None:
        """Share verified inbox editor records with other synced workstations."""
        cloud = snapshot(self.project_root)
        with self.work_lock:
            local = snapshot(self.local_root)
            editors = dict(self.editors)
        published = read_editors(self.project_root)
        updates = {}
        for relative, editor in editors.items():
            fingerprint = editor.get("fingerprint")
            if not fingerprint or local.get(relative) != fingerprint or cloud.get(relative) != fingerprint:
                continue
            existing = published.get(relative, {})
            if (existing.get("fingerprint") == fingerprint
                    and str(existing.get("modified_at", "")) >= str(editor.get("modified_at", ""))):
                continue
            updates[relative] = editor
        if updates:
            write_editors(self.project_root, updates)

    def start(self) -> None:
        self.thread = threading.Thread(target=self._loop, name="review-onedrive-sync", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=2)

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.sync_once()
            except Exception as error:
                with self.lock:
                    self.status.update({"state": "offline", "error": str(error)})
                    self._save_manifest()
            self.wake.wait(SYNC_INTERVAL)
            self.wake.clear()

    def sync_once(self) -> None:
        with self.sync_lock:
            self._sync_once()

    def _sync_once(self) -> None:
        # OneDrive scans and transfers stay outside the request lock. A slow or
        # unavailable OneDrive folder therefore cannot stall local UI requests.
        remote = snapshot(self.project_root)
        cloud_editors = read_editors(self.project_root)
        with self.work_lock:
            local = snapshot(self.local_root)
            baseline = dict(self.baseline)
        paths = set(remote) | set(local) | set(baseline)
        conflicts = []
        push = []
        pull = []
        equal = []
        adopt_remote = []
        for relative in sorted(paths):
            old, current, upstream = baseline.get(relative), local.get(relative), remote.get(relative)
            local_changed = current != old
            remote_changed = upstream != old
            if local_changed and remote_changed and current == upstream:
                equal.append(relative)
            elif local_changed and remote_changed and current != upstream:
                if (relative.endswith(".xlsx") and current is not None and upstream is not None
                        and same_workbook_content(self.local_root / relative,
                                                  self.project_root / relative)):
                    adopt_remote.append(relative)
                else:
                    conflicts.append(relative)
            elif local_changed and current != upstream:
                if review_owned(relative):
                    push.append(relative)
                else:
                    conflicts.append(relative)
            elif remote_changed and current != upstream:
                pull.append(relative)
        if equal:
            with self.lock:
                for relative in equal:
                    if local.get(relative) is None:
                        self.baseline.pop(relative, None)
                    else:
                        self.baseline[relative] = local[relative]
                self._save_manifest()
        if conflicts:
            with self.lock:
                self.status.update({"state": "conflict", "conflicts": conflicts,
                                    "pending": len(push), "error": None})
                self._save_manifest()
            return
        for relative in adopt_remote:
            source = self.project_root / relative
            temporary = self.directory / "inbound" / relative
            atomic_copy(source, temporary)
            if digest(temporary) != remote[relative]:
                raise RuntimeError(f"OneDrive changed during sync: {relative}")
            with self.work_lock:
                destination = self.local_root / relative
                if digest(destination) != local[relative]:
                    raise RuntimeError(f"Local review changed during sync: {relative}")
                atomic_copy(temporary, destination)
                self.baseline[relative] = remote[relative]
                editor = cloud_editors.get(relative)
                if isinstance(editor, dict) and editor.get("fingerprint") == remote[relative]:
                    self.editors[relative] = editor
                else:
                    self.editors.pop(relative, None)
                self._save_manifest()
            temporary.unlink(missing_ok=True)
        with self.lock:
            self.status.update({"state": "syncing", "conflicts": [],
                                "pending": len(push), "error": None})
            self._save_manifest()
        # Stage a stable local snapshot before publishing. Local review actions
        # may continue while OneDrive is slow, and later edits stay pending.
        staging = self.directory / "outbound"
        shutil.rmtree(staging, ignore_errors=True)
        staged = {}
        with self.work_lock:
            for relative in push:
                source = self.local_root / relative
                if source.is_file():
                    destination = staging / relative
                    atomic_copy(source, destination)
                    staged[relative] = digest(destination)
                else:
                    staged[relative] = None
        try:
            # Trackers first, archives next, pending deletions last.
            push.sort(key=lambda name: (name.startswith("workspace/.system/proposed-updates/"), name))
            for relative in push:
                destination = self.project_root / relative
                observed = digest(destination) if destination.is_file() else None
                if observed != remote.get(relative):
                    raise RuntimeError(f"OneDrive changed during sync: {relative}")
                source = staging / relative
                if staged[relative] is None:
                    destination.unlink(missing_ok=True)
                else:
                    atomic_copy(source, destination)
                with self.lock:
                    if staged[relative] is None:
                        self.baseline.pop(relative, None)
                    else:
                        self.baseline[relative] = staged[relative]
                    self._save_manifest()
            for relative in pull:
                source = self.project_root / relative
                temporary = self.directory / "inbound" / relative
                if source.is_file():
                    atomic_copy(source, temporary)
                    incoming = digest(temporary)
                    if incoming != remote[relative]:
                        raise RuntimeError(f"OneDrive changed during sync: {relative}")
                else:
                    incoming = None
                with self.work_lock:
                    destination = self.local_root / relative
                    observed = digest(destination) if destination.is_file() else None
                    if observed != local.get(relative):
                        raise RuntimeError(f"Local review changed during sync: {relative}")
                    if incoming is None:
                        destination.unlink(missing_ok=True)
                        self.baseline.pop(relative, None)
                        self.editors.pop(relative, None)
                    else:
                        atomic_copy(temporary, destination)
                        self.baseline[relative] = incoming
                        editor = cloud_editors.get(relative)
                        if isinstance(editor, dict) and editor.get("fingerprint") == incoming:
                            self.editors[relative] = editor
                        else:
                            self.editors.pop(relative, None)
                    self._save_manifest()
                temporary.unlink(missing_ok=True)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        with self.work_lock:
            current_local = snapshot(self.local_root)
        with self.lock:
            pending = sum(current_local.get(name) != value for name, value in self.baseline.items())
            pending += len(set(current_local) - set(self.baseline))
            self.status.update({"state": "local" if pending else "synced", "pending": pending,
                                "last_success": now(), "error": None})
            self._save_manifest()
        self.publish_cloud_editors()
        self.refresh_sources()

    def refresh_sources(self) -> None:
        """Refresh non-review evidence independently from tracker publishing."""
        try:
            upstream = files(self.project_root)
        except OSError:
            return
        for relative, source in upstream.items():
            if review_owned(relative):
                continue
            destination = self.local_root / relative
            try:
                if destination.is_file():
                    local_stat, remote_stat = destination.stat(), source.stat()
                    if (local_stat.st_size == remote_stat.st_size
                            and local_stat.st_mtime_ns >= remote_stat.st_mtime_ns):
                        continue
                atomic_copy(source, destination)
            except OSError:
                # Keep the last usable local source copy if OneDrive is slow.
                continue
