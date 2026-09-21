#!/usr/bin/env python3
"""Run the loopback-only visual review inbox.

Usage:
    py review_server.py start [--root OPPORTUNITY]
    py review_server.py status [--root OPPORTUNITY]
    py review_server.py wait [--root OPPORTUNITY] [--after N] [--timeout SECONDS]
    py review_server.py stop [--root OPPORTUNITY]
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SCRIPT = Path(__file__).resolve()
PLUGIN_ROOT = SCRIPT.parents[2]
SOURCE_APP_DIR = PLUGIN_ROOT / "skills" / "review-updates" / "assets" / "review-app"
INSTALLED_APP_DIR = PLUGIN_ROOT / "review-updates" / "assets" / "review-app"
APP_DIR = SOURCE_APP_DIR if SOURCE_APP_DIR.is_dir() else INSTALLED_APP_DIR
STARTED_PROCESSES: dict[str, subprocess.Popen] = {}
CONFIGURED_ROOT: Path | None = None


def configure_root(root: Path) -> None:
    global CONFIGURED_ROOT
    resolved = root.resolve()
    if CONFIGURED_ROOT == resolved:
        return
    os.environ["ASCENT_OPPORTUNITY_ROOT"] = str(resolved)
    for module in ("paths", "trackers", "validate_updates", "review_store"):
        sys.modules.pop(module, None)
    CONFIGURED_ROOT = resolved


def state_path(root: Path) -> Path:
    return root / "workspace" / ".system" / "review-server.json"


def read_state(root: Path) -> dict | None:
    path = state_path(root)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def write_state(root: Path, state: dict) -> None:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def request_json(url: str, method: str = "GET", token: str = "",
                 body: dict | None = None, timeout: float = 2.0) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-Review-Token"] = token
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def healthy(state: dict | None) -> bool:
    if not state or not state.get("port"):
        return False
    try:
        result = request_json(f"http://127.0.0.1:{state['port']}/api/health")
        return result.get("ok") is True and result.get("instance_id") == state.get("instance_id")
    except (OSError, ValueError, urllib.error.URLError):
        return False


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], token: str, root: Path, instance_id: str):
        super().__init__(address, ReviewHandler)
        self.review_token = token
        self.root_path = root
        self.instance_id = instance_id
        self.accepted_cache: dict[str, object] = {"signature": None, "items": []}
        self.link_options_cache: dict[str, object] = {"signature": None, "items": []}


def accepted_cache_signature(root: Path, schema: dict) -> tuple[tuple[str, int, int], ...]:
    paths = [root / definition["tracker_file"] for definition in schema["categories"].values()]
    applied = root / "workspace" / ".system" / "applied-updates"
    paths.extend(applied.glob("*.y*ml"))
    return tuple(sorted((str(path), path.stat().st_mtime_ns, path.stat().st_size)
                        for path in paths if path.is_file()))


def accepted_items(server: ReviewServer) -> list[dict]:
    from paths import load_schema
    from trackers import id_column, read_rows
    import review_store

    schema = load_schema()
    signature = accepted_cache_signature(server.root_path, schema)
    if server.accepted_cache["signature"] == signature:
        return server.accepted_cache["items"]
    evidence_index = review_store.applied_evidence_index()
    items = []
    for category, definition in schema["categories"].items():
        try:
            rows = read_rows(category, schema)
        except FileNotFoundError:
            rows = []
        for row in rows:
            source_refs = [ref.strip() for ref in str(row.get("Source Refs", "")).split(schema["list_delimiter"]) if ref.strip()]
            tracker_id = row.get(id_column(category, schema), "")
            title = review_store.display_label(category, row, schema)
            items.append({
                "category": category,
                "category_label": category.replace("_", " ").title(),
                "tracker_id": tracker_id,
                "title": title,
                "status": row.get("Status", ""),
                "fields": row,
                "field_schema": definition.get("columns", []),
                "source_refs": source_refs,
                "evidence": review_store.accepted_evidence(category, tracker_id, row, source_refs, evidence_index),
            })
    server.accepted_cache = {
        "signature": signature,
        "items": items,
    }
    return items


def accepted_link_options(server: ReviewServer) -> list[dict]:
    """Return link picker data without reconstructing evidence."""
    from paths import load_schema
    from trackers import id_column, read_rows
    import review_store

    schema = load_schema()
    signature = tuple(sorted((str(path), path.stat().st_mtime_ns, path.stat().st_size)
                             for path in {server.root_path / definition["tracker_file"]
                                          for definition in schema["categories"].values()} if path.is_file()))
    if server.link_options_cache["signature"] == signature:
        return server.link_options_cache["items"]
    items = []
    for category, definition in schema["categories"].items():
        for row in read_rows(category, schema):
            title = review_store.display_label(category, row, schema)
            items.append({"category": category, "category_label": category.replace("_", " ").title(),
                          "tracker_id": row.get(id_column(category, schema), ""), "title": title, "fields": row})
    server.link_options_cache = {"signature": signature, "items": items}
    return items


class ReviewHandler(BaseHTTPRequestHandler):
    server: ReviewServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_common_headers(self, status: int,
                            content_type: str = "application/json; charset=utf-8",
                            length: int | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; script-src 'self'; style-src 'self'; "
                         "font-src 'self'; img-src 'self' data:; connect-src 'self'; "
                         "object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.end_headers()

    def json(self, status: int, value: dict) -> None:
        payload = json.dumps(value, default=str).encode()
        self.send_common_headers(status, length=len(payload))
        self.wfile.write(payload)

    def file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.json(404, {"error": "not found"})
            return
        payload = path.read_bytes()
        self.send_common_headers(200, content_type, len(payload))
        self.wfile.write(payload)

    def parsed(self) -> tuple[str, dict[str, list[str]]]:
        value = urllib.parse.urlparse(self.path)
        return value.path, urllib.parse.parse_qs(value.query)

    def require_token(self) -> bool:
        supplied = self.headers.get("X-Review-Token", "")
        origin = self.headers.get("Origin")
        expected_origins = {
            f"http://127.0.0.1:{self.server.server_port}",
            f"http://localhost:{self.server.server_port}",
        }
        if origin and origin not in expected_origins:
            self.json(403, {"error": "origin is not allowed"})
            return False
        if not secrets.compare_digest(supplied, self.server.review_token):
            self.json(403, {"error": "valid session token required"})
            return False
        return True

    def body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("invalid content length")
        if length <= 0 or length > 1_000_000:
            raise ValueError("request body must be between 1 byte and 1 MB")
        try:
            value = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("malformed JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def do_GET(self) -> None:
        configure_root(self.server.root_path)
        import review_store

        path, query = self.parsed()
        if path == "/api/health":
            self.json(200, {"ok": True, "instance_id": self.server.instance_id,
                            "pid": os.getpid(), "root": str(self.server.root_path)})
            return
        if path == "/api/inbox":
            self.json(200, review_store.list_cards())
            return
        if path == "/api/accepted":
            self.json(200, {"items": accepted_items(self.server)})
            return
        if path == "/api/link-options":
            self.json(200, {"items": accepted_link_options(self.server)})
            return
        if path == "/source":
            source_ref = query.get("path", [""])[0]
            candidate = (self.server.root_path / source_ref).resolve()
            try:
                candidate.relative_to(self.server.root_path / "workspace")
            except ValueError:
                self.json(403, {"error": "source path is outside the workspace"})
                return
            content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            self.file(candidate, content_type)
            return
        if path == "/api/reveal-source":
            if not self.require_token():
                return
            source_ref = query.get("path", [""])[0]
            candidate = (self.server.root_path / source_ref).resolve()
            try:
                candidate.relative_to(self.server.root_path / "workspace")
            except ValueError:
                self.json(403, {"error": "source path is outside the workspace"})
                return
            if not candidate.is_file():
                self.json(404, {"error": "source file was not found"})
                return
            try:
                subprocess.run(["open", "-R", str(candidate)], check=True, capture_output=True)
            except (OSError, subprocess.CalledProcessError):
                self.json(500, {"error": "Finder could not reveal the source file"})
                return
            self.json(200, {"revealed": source_ref})
            return
        if path == "/api/events":
            try:
                after = int(query.get("after", ["0"])[0])
                timeout = min(25.0, max(0.0, float(query.get("timeout", ["20"])[0])))
            except ValueError:
                self.json(400, {"error": "after and timeout must be numeric"})
                return
            deadline = time.monotonic() + timeout
            while True:
                result = review_store.queue_after(after)
                if result["items"] or time.monotonic() >= deadline:
                    self.json(200, result)
                    return
                time.sleep(0.2)
        static = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/accepted": ("index.html", "text/html; charset=utf-8"),
            "/app.css": ("app.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/vendor/anime.esm.min.js": ("vendor/anime.esm.min.js", "text/javascript; charset=utf-8"),
            "/fonts/slalom-sans-regular.woff2": ("fonts/slalom-sans-regular.woff2", "font/woff2"),
            "/fonts/slalom-sans-bold.woff2": ("fonts/slalom-sans-bold.woff2", "font/woff2"),
            "/logo.svg": ("logo.svg", "image/svg+xml"),
        }
        if path in static:
            name, content_type = static[path]
            self.file(APP_DIR / name, content_type)
            return
        self.json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self.require_token():
            return
        configure_root(self.server.root_path)
        import review_store

        path, _query = self.parsed()
        routes = {
            "/api/autosave": lambda body: review_store.autosave(
                body.get("proposal_id", ""), body.get("revision"), body.get("fields")),
            "/api/accept": lambda body: review_store.accept(
                body.get("proposal_id", ""), body.get("revision"),
                self.headers.get("Idempotency-Key", "")),
            "/api/reject": lambda body: review_store.reject(
                body.get("proposal_id", ""), body.get("revision"), str(body.get("reason", ""))),
            "/api/flag": lambda body: review_store.flag(
                body.get("proposal_id", ""), body.get("revision"), str(body.get("note", ""))),
            "/api/create": lambda body: review_store.create(
                str(body.get("category", "")), str(body.get("source_ref", ""))),
            "/api/accepted/reject": lambda body: review_store.reject_accepted(
                str(body.get("category", "")), str(body.get("tracker_id", "")), str(body.get("reason", ""))),
            "/api/accepted/pending": lambda body: review_store.move_accepted_to_pending(
                str(body.get("category", "")), str(body.get("tracker_id", ""))),
        }
        if path == "/api/stop":
            self.json(200, {"stopping": True})
            import threading
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if path == "/api/accepted/update":
            from paths import load_schema
            from trackers import id_column, upsert_row

            body = self.body()
            category = str(body.get("category", ""))
            schema = load_schema()
            if category not in schema["categories"]:
                self.json(400, {"error": "unknown tracker category"})
                return
            fields = body.get("fields")
            if not isinstance(fields, dict):
                self.json(400, {"error": "fields must be an object"})
                return
            fields[id_column(category, schema)] = str(body.get("tracker_id", ""))
            try:
                tracker_id = upsert_row(category, fields, schema)
            except (TypeError, ValueError) as exc:
                self.json(422, {"error": str(exc)})
                return
            self.json(200, {"tracker_id": tracker_id})
            return
        if path not in routes:
            self.json(404, {"error": "not found"})
            return
        try:
            result = routes[path](self.body())
            self.json(200, result)
        except review_store.ReviewError as exc:
            value = {"error": str(exc)}
            if hasattr(exc, "problems"):
                value["validation"] = exc.problems
            self.json(exc.status, value)
        except ValueError as exc:
            self.json(400, {"error": str(exc)})
        except Exception as exc:
            self.json(500, {"error": f"review operation failed: {exc}"})

    def do_PUT(self) -> None:
        self.json(405, {"error": "method not allowed"})

    do_PATCH = do_PUT
    do_DELETE = do_PUT


def serve(root: Path, token: str, instance_id: str) -> int:
    configure_root(root)
    server = ReviewServer(("127.0.0.1", 0), token, root, instance_id)
    state = {
        "pid": os.getpid(),
        "port": server.server_port,
        "token": token,
        "instance_id": instance_id,
        "root": str(root),
        "started_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_state(root, state)
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
        current = read_state(root)
        if current and current.get("instance_id") == instance_id:
            state_path(root).unlink(missing_ok=True)
    return 0


def start(root: Path) -> int:
    state = read_state(root)
    if healthy(state):
        print(f"review inbox ready: http://127.0.0.1:{state['port']}/?session={state['token']}")
        return 0
    state_path(root).unlink(missing_ok=True)
    token = secrets.token_urlsafe(32)
    instance_id = str(secrets.token_hex(16))
    log = root / "workspace" / ".system" / "review-server.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "ab") as output:
        process = subprocess.Popen(
            [sys.executable, str(SCRIPT), "serve", "--root", str(root),
             "--token", token, "--instance-id", instance_id],
            stdin=subprocess.DEVNULL, stdout=output, stderr=output,
            start_new_session=True,
        )
        STARTED_PROCESSES[instance_id] = process
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        state = read_state(root)
        if healthy(state):
            print(f"review inbox ready: http://127.0.0.1:{state['port']}/?session={state['token']}")
            return 0
        time.sleep(0.1)
    print(f"review server did not become healthy; see {log}", file=sys.stderr)
    return 1


def status(root: Path) -> int:
    state = read_state(root)
    if healthy(state):
        print(json.dumps({"running": True, "pid": state["pid"], "port": state["port"],
                          "url": f"http://127.0.0.1:{state['port']}/?session={state['token']}"}))
        return 0
    state_path(root).unlink(missing_ok=True)
    print(json.dumps({"running": False}))
    return 1


def stop(root: Path) -> int:
    state = read_state(root)
    if not healthy(state):
        state_path(root).unlink(missing_ok=True)
        print("review server is not running")
        return 0
    try:
        request_json(f"http://127.0.0.1:{state['port']}/api/stop", method="POST",
                     token=state["token"], body={})
    except urllib.error.URLError as exc:
        print(f"could not stop review server: {exc}", file=sys.stderr)
        return 1
    process = STARTED_PROCESSES.pop(state.get("instance_id", ""), None)
    if process:
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass
    print("review server stopped")
    return 0


def wait_for_events(root: Path, after: int, timeout: float) -> int:
    state = read_state(root)
    if not healthy(state):
        print(json.dumps({"error": "review server is not running"}))
        return 1
    deadline = time.monotonic() + max(0, timeout)
    result = {"sequence": after, "items": []}
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        url = (f"http://127.0.0.1:{state['port']}/api/events?after={after}"
               f"&timeout={min(20, remaining):.1f}")
        result = request_json(url, timeout=min(25, remaining + 2))
        if result.get("items"):
            break
    print(json.dumps(result))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("start", "status", "stop"):
        child = subparsers.add_parser(name)
        child.add_argument("--root", type=Path, default=Path.cwd())
    waiter = subparsers.add_parser("wait")
    waiter.add_argument("--root", type=Path, default=Path.cwd())
    waiter.add_argument("--after", type=int, default=0)
    waiter.add_argument("--timeout", type=float, default=60)
    server = subparsers.add_parser("serve", help=argparse.SUPPRESS)
    server.add_argument("--root", type=Path, required=True)
    server.add_argument("--token", required=True)
    server.add_argument("--instance-id", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "serve":
        return serve(root, args.token, args.instance_id)
    if args.command == "start":
        return start(root)
    if args.command == "status":
        return status(root)
    if args.command == "stop":
        return stop(root)
    return wait_for_events(root, args.after, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
