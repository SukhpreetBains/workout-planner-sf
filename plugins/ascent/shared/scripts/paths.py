"""Repo paths and tracker-schema loading. Import this from every other script."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

# ASCENT_OPPORTUNITY_ROOT identifies the Opportunity workspace root. Default to the
# caller's working directory so plugin installation depth never affects data.
REPO_ROOT = Path(os.environ.get("ASCENT_OPPORTUNITY_ROOT")
                 or Path.cwd()).resolve()

WORKSPACE = REPO_ROOT / "workspace"
INBOX = WORKSPACE / "inbox"
TRACKERS_DIR = WORKSPACE / "trackers"
SYSTEM_DIR = WORKSPACE / ".system"

PROPOSED_UPDATES_DIR = SYSTEM_DIR / "proposed-updates"
APPLIED_UPDATES_DIR = SYSTEM_DIR / "applied-updates"
REJECTED_UPDATES_DIR = SYSTEM_DIR / "rejected-updates"
TRACKER_COPIES_DIR = SYSTEM_DIR / "tracker-copies"
AI_REVIEW_QUEUE = SYSTEM_DIR / "ai-review-queue.yaml"
REVIEW_HISTORY = SYSTEM_DIR / "review-history.jsonl"
REVIEW_IDEMPOTENCY = SYSTEM_DIR / "review-idempotency.json"
REVIEW_LOCK = SYSTEM_DIR / "review.lock"
REVIEW_SERVER_STATE = SYSTEM_DIR / "review-server.json"
SEARCH_DB = SYSTEM_DIR / "search" / "index.sqlite"
SYNC_STATE = SYSTEM_DIR / "sync-state.json"
SOURCES_FILE = SYSTEM_DIR / "sources.yaml"
PROJECT_FILE = SYSTEM_DIR / "project.yaml"

SCHEMA_FILE = Path(__file__).resolve().parents[1] / "schema" / "trackers.yaml"

# Workspace folders whose text content is searchable
INDEXED_FOLDERS = [
    "project",
    "meetings",
    "current-state",
    "future-state",
    "reference",
]
INDEXED_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".csv"}


def load_schema() -> dict:
    with open(SCHEMA_FILE, encoding="utf-8") as fh:
        schema = yaml.safe_load(fh)
    # attach each category's tracker file for convenience
    for tracker in schema["trackers"].values():
        for cat in tracker["tabs"]:
            schema["categories"][cat]["tracker_file"] = tracker["file"]
    return schema


def rel(path: Path) -> str:
    """Repo-relative POSIX string for display and Source Refs."""
    return path.resolve().relative_to(REPO_ROOT).as_posix()
