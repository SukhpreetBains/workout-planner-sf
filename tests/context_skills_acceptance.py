#!/usr/bin/env python3
"""Run focused, synthetic acceptance fixtures for discovery and retrieval contracts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "plugins" / "ascent" / "skills"
DISCOVERY = SKILLS_ROOT / "investigate-project" / "scripts" / "project_context.py"
SOURCE_CONTEXT = SKILLS_ROOT / "ascent-initial-setup" / "scripts" / "manage-source-context.py"
RANK = SKILLS_ROOT / "investigate-project" / "scripts" / "rank_context.py"
PERSIST = SKILLS_ROOT / "investigate-project" / "scripts" / "persist_context.py"
CACHE = SKILLS_ROOT / "investigate-project" / "scripts" / "cache_context.py"
VALIDATOR = ROOT / "tests" / "validate_context_skills.py"


def run(*args: str) -> str:
    result = subprocess.run([sys.executable, *args], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed: {result.stderr.strip()}")
    return result.stdout


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    run(str(VALIDATOR))
    with tempfile.TemporaryDirectory(prefix="context-fixture-") as temp:
        root = Path(temp)
        context = root / "workspace" / ".system" / "project-context"
        source_context = root / "workspace" / ".system" / "source-context.yaml"
        run(str(SOURCE_CONTEXT), "init", "--root", str(root), "--account", "Synthetic Account", "--project", "Synthetic")
        shared = ["--root", str(root), "--authority", "canonical", "--priority", "5", "--sensitivity", "internal"]
        run(str(SOURCE_CONTEXT), "upsert-source", *shared, "--id", "chat", "--kind", "slack", "--name", "Chat source", "--locator", "slack://team/channel", "--identifier", "parent_id=team", "--identifier", "channel_id=channel", "--purpose", "Decisions about context boundaries", "--access-state", "available")
        run(str(SOURCE_CONTEXT), "upsert-source", *shared, "--id", "document", "--kind", "sharepoint", "--name", "Document source", "--locator", "https://tenant.sharepoint.com/sites/Delivery/Shared%20Documents/Synthetic", "--identifier", "hostname=tenant.sharepoint.com", "--identifier", "site_path=/sites/Delivery", "--identifier", "drive_name=Shared Documents", "--identifier", "folder_path=Synthetic", "--purpose", "Requirements and acceptance criteria", "--access-state", "available")
        run(str(SOURCE_CONTEXT), "upsert-source", *shared, "--id", "denied", "--kind", "teams", "--name", "Restricted chat", "--locator", "teams://team/private", "--purpose", "Permission denied decision history", "--status", "scope_not_verified", "--connection-state", "not connected", "--access-state", "unavailable", "--access-reason", "Permission denied by the recorded source boundary.")
        run(str(SOURCE_CONTEXT), "validate", "--root", str(root))
        run(str(DISCOVERY), "init", "--root", str(root), "--name", "Synthetic", "--objective", "Test context boundaries")
        run(str(DISCOVERY), "set-project", "--root", str(root), "--phase", "validation")
        run(str(DISCOVERY), "import-source-context", "--root", str(root))

        run(str(DISCOVERY), "record-discovery", "--root", str(root), "--sources-considered", "7", "--sources-recorded", "2", "--connector-calls", "3", "--items-inspected", "30", "--characters-inspected", "97", "--cap", "chat=4", "--cap", "document=6")
        manifest = load(context / "manifest.json")
        assert manifest["discovery_runs"][-1]["estimated_tokens"] == 25
        assert manifest["discovery_runs"][-1]["exploration_caps"]["chat"] == 4
        assert manifest["source_context"]["path"] == "workspace/.system/source-context.yaml"
        assert manifest["source_context"]["source_count"] == 3
        assert {source["kind"] for source in manifest["sources"]} == {"slack", "teams", "sharepoint"}
        assert any(source["kind"] == "sharepoint" and source["locator"].startswith("https://tenant.sharepoint.com/") for source in manifest["sources"])
        manifest_text = (context / "manifest.json").read_text(encoding="utf-8").lower()
        shared_text = source_context.read_text(encoding="utf-8").lower()
        assert "restricted secret transcript content" not in manifest_text
        assert "message body" not in manifest_text
        assert "restricted secret transcript content" not in shared_text
        assert "message body" not in shared_text

        chunks = root / "chunks.jsonl"
        dense = "boundary evidence " * 100
        chunks.write_text("\n".join(json.dumps({"chunk_id": f"chunk-{i}", "source_id": "document", "title": "Boundary requirement", "text": dense}) for i in range(8)) + "\n", encoding="utf-8")
        ranked = root / "ranked.jsonl"
        gaps = root / "access-gaps.json"
        run(str(RANK), "--manifest", str(context / "manifest.json"), "--chunks", str(chunks), "--task", "context boundary evidence", "--output", str(ranked), "--top-n", "24", "--max-per-source", "6", "--gaps-output", str(gaps))
        ranked_items = [json.loads(line) for line in ranked.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert ranked_items and sum(len(item["text"]) for item in ranked_items) <= manifest["source_policy"]["max_total_chars"]

        denied_chunks = root / "denied-chunks.jsonl"
        denied_chunks.write_text("\n".join([
            json.dumps({"chunk_id": "allowed-1", "source_id": "document", "text": "Accessible boundary evidence"}),
            json.dumps({"chunk_id": "denied-1", "source_id": "denied", "text": "Restricted secret transcript content"}),
        ]) + "\n", encoding="utf-8")
        denied_ranked = root / "denied-ranked.jsonl"
        denied_gaps = root / "denied-gaps.json"
        run(str(RANK), "--manifest", str(context / "manifest.json"), "--chunks", str(denied_chunks), "--task", "boundary evidence", "--output", str(denied_ranked), "--gaps-output", str(denied_gaps))
        assert "Restricted secret transcript content" not in denied_ranked.read_text(encoding="utf-8")
        gap_items = load(denied_gaps)
        assert any(item["source_id"] == "denied" and item["state"] == "unavailable" for item in gap_items)

        pack = root / "pack.json"
        pack.write_text(json.dumps({
            "task": "context boundary evidence",
            "overview": "Accessible evidence was retained.",
            "decisions": [],
            "open_questions": [],
            "access_gaps": gap_items,
            "sources": [{"source_id": "document", "summary": "Requirements source", "excerpts": [ranked_items[0]]}],
        }), encoding="utf-8")
        run(str(PERSIST), "--manifest", str(context / "manifest.json"), "--pack", str(pack), "--context-dir", str(context), "--gaps", str(denied_gaps))
        index = (context / "index.md").read_text(encoding="utf-8")
        assert "## Access Gaps" in index and "Restricted chat" in index and "Restricted secret transcript content" not in index
        cache_result = json.loads(run(str(CACHE), "--manifest", str(context / "manifest.json"), "--context-dir", str(context), "--source-id", "document", "--task", "requirements acceptance criteria", "--now", "2099-01-01T00:00:00Z"))
        assert cache_result["reuse"] is False  # the source uses the default finite freshness window
        cache_result = json.loads(run(str(CACHE), "--manifest", str(context / "manifest.json"), "--context-dir", str(context), "--source-id", "document", "--task", "requirements acceptance criteria", "--now", cache_result["cached_at"]))
        # Reusing at the recorded retrieval timestamp is deterministic and requires no connector call.
        assert cache_result["reuse"] is True, cache_result
        run(str(SOURCE_CONTEXT), "upsert-source", *shared, "--id", "document", "--kind", "sharepoint", "--name", "Document source", "--locator", "https://tenant.sharepoint.com/sites/Delivery/Shared%20Documents/Synthetic-v2", "--identifier", "hostname=tenant.sharepoint.com", "--identifier", "site_path=/sites/Delivery", "--identifier", "drive_name=Shared Documents", "--identifier", "folder_path=Synthetic-v2", "--purpose", "Requirements and acceptance criteria", "--access-state", "available")
        run(str(DISCOVERY), "import-source-context", "--root", str(root))
        changed_locator = json.loads(run(str(CACHE), "--manifest", str(context / "manifest.json"), "--context-dir", str(context), "--source-id", "document", "--task", "requirements acceptance criteria", "--now", cache_result["cached_at"]))
        assert changed_locator["reuse"] is False
        assert "locator changed" in changed_locator["reason"]

    # The shared YAML manager remains usable when PyYAML is absent from the runtime.
    with tempfile.TemporaryDirectory(prefix="source-context-fallback-") as temp:
        root = Path(temp)
        run("-S", str(SOURCE_CONTEXT), "init", "--root", str(root), "--account", "Fallback Account", "--project", "Fallback Project")
        run("-S", str(SOURCE_CONTEXT), "upsert-source", "--root", str(root), "--id", "fallback-folder", "--kind", "sharepoint", "--name", "Fallback folder", "--locator", "https://tenant.sharepoint.com/sites/Test/Shared%20Documents/Fallback", "--identifier", "hostname=tenant.sharepoint.com", "--identifier", "site_path=/sites/Test", "--identifier", "folder_path=Fallback", "--purpose", "Fallback parser validation")
        exported = json.loads(run("-S", str(SOURCE_CONTEXT), "export", "--root", str(root)))
        assert exported["sources"][0]["id"] == "fallback-folder"
        assert exported["sources"][0]["kind"] == "sharepoint"

    # Gada's original messaging-only shape remains importable and is preserved when extended.
    with tempfile.TemporaryDirectory(prefix="source-context-gada-") as temp:
        root = Path(temp)
        source_context = root / "workspace" / ".system" / "source-context.yaml"
        source_context.parent.mkdir(parents=True)
        source_context.write_text(
            """account: Acme
project: Service Transformation
last_verified: 2026-08-11
messaging_platforms:
  - name: Slack
    connection_state: usable
    locations:
      - name: account-acme
        parent_name: Client workspace
        identifiers:
          channel_id: C456
          parent_id: T123
        description: Account delivery coordination
        status: confirmed
""",
            encoding="utf-8",
        )
        exported = json.loads(run("-S", str(SOURCE_CONTEXT), "export", "--root", str(root)))
        assert exported["sources"][0]["kind"] == "slack"
        assert exported["sources"][0]["access"]["state"] == "available"
        run("-S", str(SOURCE_CONTEXT), "upsert-source", "--root", str(root), "--id", "engagement-folder", "--kind", "sharepoint", "--name", "Engagement folder", "--locator", "https://tenant.sharepoint.com/sites/Test/Shared%20Documents/Acme/Service", "--purpose", "Canonical engagement workspace")
        exported = json.loads(run("-S", str(SOURCE_CONTEXT), "export", "--root", str(root)))
        assert {source["kind"] for source in exported["sources"]} == {"slack", "sharepoint"}
    print("Passed discovery/retrieval acceptance fixtures")


if __name__ == "__main__":
    main()
