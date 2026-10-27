#!/usr/bin/env python3
"""Create and open a disposable, synthetic Project review workspace.

Run: python3 plugins/ascent/shared/scripts/review_demo.py
Use --prepare-only to create the files without starting a browser or server.
Each default run creates a fresh directory under the operating system's temporary
directory, so old browser tabs cannot edit a new session. Pass --root PATH to
reset a specific directory previously marked by this script.
"""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

SCRIPT = Path(__file__).resolve()
SCRIPTS = SCRIPT.parent
DEFAULT_ROOT = Path(tempfile.gettempdir()) / f"ascent-workspace-review-demo-{secrets.token_hex(4)}"
MARKER = ".ascent-review-demo"


def ensure_dependencies() -> None:
    check = "import yaml, openpyxl"
    candidates = [Path(sys.executable)]
    candidates.extend(sorted((Path.home() / ".ascent" / "venvs").glob("*/bin/python")))
    for candidate in candidates:
        result = subprocess.run([str(candidate), "-c", check], capture_output=True)
        if result.returncode == 0:
            if candidate != Path(sys.executable):
                os.execv(str(candidate), [str(candidate), str(SCRIPT), *sys.argv[1:]])
            return
    raise SystemExit("PyYAML and openpyxl are required. Install the Ascent shared requirements first.")


ensure_dependencies()
import yaml


def write_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")


def proposal(category: str, fields: dict, excerpt: str, line: int, source: str,
             *, action: str = "add", tracker_id: str | None = None,
             review: dict | None = None, proposal_id: str | None = None) -> dict:
    item = {
        "category": category,
        "action": action,
        "fields": fields,
        "source_refs": [source],
        "evidence": [{"source_ref": source, "excerpt": excerpt, "line_start": line}],
    }
    if tracker_id:
        item["id"] = tracker_id
    if proposal_id:
        item["proposal_id"] = proposal_id
    if review:
        item["review"] = review
    return item


def prepare(root: Path) -> None:
    root = root.expanduser().resolve()
    if root.exists():
        if not (root / MARKER).is_file():
            raise SystemExit(f"Refusing to replace an unmarked directory: {root}")
        if (root / "workspace/.system/review-server.json").is_file():
            stopped = subprocess.run([sys.executable, str(SCRIPTS / "review_server.py"),
                                      "stop", "--root", str(root)],
                                     capture_output=True, text=True,
                                     env={**os.environ, "ASCENT_PROJECT_ROOT": str(root)})
            if stopped.returncode:
                raise SystemExit(f"Could not stop the current demo server: {stopped.stderr.strip()}")
        shutil.rmtree(root)
    root.mkdir(parents=True)
    (root / MARKER).write_text("Synthetic workspace. Safe to reset with review_demo.py.\n", encoding="utf-8")
    for name in ("project", "trackers", "inbox", ".system"):
        (root / "workspace" / name).mkdir(parents=True, exist_ok=True)
    os.environ["ASCENT_PROJECT_ROOT"] = str(root)

    from trackers import init_trackers, upsert_row
    from paths import load_schema

    write_yaml(root / "workspace/.system/project.yaml", {
        "account": "Cedar Vale Cooperative (synthetic)",
        "project": "Service Intake Modernization Demo",
        "industry": "none",
    })
    init_trackers()
    source = "workspace/meetings/2026-09-24 - Intake workshop.md"
    note = (
        "# Synthetic intake workshop\n"
        "All people, organizations, systems, and observations in this note are fictional.\n"
        "Maya Torres owns service operations and approves intake process changes.\n"
        "Requests arrive in a shared mailbox and coordinators rekey them into QueueBoard.\n"
        "The rekeying step adds two business days to about 40 percent of requests.\n"
        "QueueBoard is the current request tracking application.\n"
        "Leadership wants 90 percent of requests assigned within one business day.\n"
        "The new intake flow must capture a request category before assignment.\n"
        "If the pilot team is unavailable, the rollout may miss its October checkpoint.\n"
        "The team decided to pilot with one region before expanding.\n"
        "Who will own category definitions after the pilot?\n"
    )
    note_path = root / source
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(note, encoding="utf-8")
    delivery_source = "workspace/meetings/2026-09-25 - Delivery planning.md"
    delivery_lines = [
        "# Synthetic delivery planning",
        "All delivery details below are fictional.",
        "The plan assumes regional coordinators can spend four hours a week on the pilot.",
        "The pilot team currently lacks a confirmed test environment, blocking rehearsal.",
        "The signed budget caps pilot support at 120 hours.",
        "The integration team must provide a sandbox feed before the pilot rehearsal.",
        "Maya will host a 60-minute category workshop on October 2.",
        "A pilot steering group will own scope decisions and escalate blockers to Maya.",
        "The pilot rehearsal is a milestone targeted for October 15.",
        "In the intake workflow, Triage follows Capture when category and contact details are present.",
        "The team agreed to log decisions in the shared register within one business day.",
        "Maya will confirm the pilot staffing roster by October 1.",
        "A separate proposal intentionally lacks a required description so designers can see the validation state.",
    ]
    delivery_path = root / delivery_source
    delivery_path.write_text("\n".join(delivery_lines) + "\n", encoding="utf-8")
    schema = load_schema()
    person_id = upsert_row("person", {
        "Name": "Maya Torres", "Description": "Owns service operations; approves intake process changes.",
        "Status": "active", "Source Refs": source,
    }, schema)
    system_id = upsert_row("system", {
        "Name": "QueueBoard", "Status": "active",
        "Description": "Fictional request tracking application", "Source Refs": source,
    }, schema)
    write_yaml(root / "workspace/.system/applied-updates/demo-person.yaml", {
        "source_refs": [source], "tracker_id": person_id,
        "review_decision": "accepted",
        "updates": [proposal("person", {"Name": "Maya Torres",
                              "Description": "Owns service operations; approves intake process changes."},
                             "Maya Torres owns service operations and approves intake process changes.",
                             3, source)],
    })
    write_yaml(root / "workspace/.system/rejected-updates/demo-out-of-scope.yaml", {
        "source_refs": [source], "review_decision": "rejected",
        "updates": [proposal("requirement", {"Name": "Buy every intake tool",
                              "Description": "Buy every intake tool on the market.", "Status": "proposed"},
                             "The new intake flow must capture a request category before assignment.",
                             8, source)],
    })

    role_id = "demo-role-service-operations-lead"
    pilot_id = "demo-phase-regional-pilot"
    risk_id = "demo-risk-pilot-staffing"
    updates = [
        proposal("person", {"Name": "Maya Torres",
                 "Description": "Owns service operations; approves intake process changes and the regional pilot.",
                 "Relationships": f"holds_role: {role_id}"},
                 "Maya Torres owns service operations and approves intake process changes.", 3,
                 source, action="update", tracker_id=person_id),
        proposal("role", {"Name": "Service Operations Lead", "Status": "active",
                 "Description": "Approves intake process changes."},
                 "Maya Torres owns service operations and approves intake process changes.", 3,
                 source, proposal_id=role_id),
        proposal("system", {"Name": "QueueBoard", "Status": "active",
                 "Description": "Application that tracks requests in the current process and provides pilot exports."},
                 "QueueBoard is the current request tracking application.", 6, source,
                 action="update", tracker_id=system_id),
        proposal("phase", {"Name": "Regional pilot", "Status": "planned",
                 "Description": "Pilot of the new intake flow in one region before expanding."},
                 "The team decided to pilot with one region before expanding.", 10, source,
                 proposal_id=pilot_id),
        proposal("pain_point", {"Name": "Manual rekeying delays assignment",
                 "Description": "Coordinators rekey mailbox requests into QueueBoard, adding two business days for about 40 percent of requests.",
                 "Status": "active", "Relationships": f"raised_by: {person_id}; impacts: {system_id}"},
                 "The rekeying step adds two business days to about 40 percent of requests.", 5, source),
        proposal("objective", {"Name": "Faster request assignment",
                 "Description": "Assign 90 percent of requests within one business day.", "Status": "active"},
                 "Leadership wants 90 percent of requests assigned within one business day.", 7, source),
        proposal("requirement", {"Name": "Category captured before assignment",
                 "Description": "The new intake flow must capture a request category before assignment.",
                 "Status": "proposed"},
                 "The new intake flow must capture a request category before assignment.", 8, source),
        proposal("risk", {"Name": "Pilot staffing",
                 "Description": "If the pilot team is unavailable, the rollout may miss its October checkpoint.",
                 "Probability": 0.6, "Impact": "high", "Status": "identified",
                 "Relationships": f"owned_by: {person_id}; impacts: {pilot_id}"},
                 "If the pilot team is unavailable, the rollout may miss its October checkpoint.", 9,
                 source, proposal_id=risk_id),
        proposal("decision", {"Name": "Single-region intake pilot",
                 "Description": "Pilot the new intake flow in one region first.", "Status": "decided",
                 "Relationships": f"applies_to: {pilot_id}"},
                 "The team decided to pilot with one region before expanding.", 10, source),
        proposal("open_question", {"Name": "Owner of category definitions",
                 "Description": "Who owns category definitions after the pilot?", "Status": "open"},
                 "Who will own category definitions after the pilot?", 11, source),
        proposal("assumption", {"Name": "Coordinator pilot capacity",
                 "Description": "Regional coordinators can spend four hours weekly on the pilot.",
                 "Status": "unvalidated"},
                 delivery_lines[2], 3, delivery_source),
        proposal("issue", {"Name": "No test environment",
                 "Description": "A missing test environment blocks pilot rehearsal.", "Status": "open"},
                 delivery_lines[3], 4, delivery_source),
        proposal("constraint", {"Name": "120-hour pilot support cap",
                 "Description": "The signed budget caps pilot support at 120 hours.", "Status": "active"},
                 delivery_lines[4], 5, delivery_source),
        proposal("dependency", {"Name": "Sandbox feed for rehearsal",
                 "Description": "The pilot rehearsal depends on the integration team providing a sandbox feed.",
                 "Status": "pending"},
                 delivery_lines[5], 6, delivery_source),
        proposal("session", {"Name": "Request category workshop", "Status": "planned",
                 "Description": "60-minute workshop to agree on pilot categories.", "Date": "2026-10-02",
                 "Relationships": f"owned_by: {person_id}"},
                 delivery_lines[6], 7, delivery_source),
        proposal("governance_rule", {"Name": "Pilot steering group scope rights",
                 "Description": "A pilot steering group owns scope decisions and escalates blockers to Maya.",
                 "Status": "proposed", "Relationships": f"accountable_to: {person_id}"},
                 delivery_lines[7], 8, delivery_source),
        proposal("milestone", {"Name": "Pilot rehearsal", "Status": "planned",
                 "Description": "Pilot rehearsal checkpoint.", "Target Date": "2026-10-15",
                 "Relationships": f"part_of: {pilot_id}"},
                 delivery_lines[8], 9, delivery_source),
        proposal("business_process", {"Name": "Intake triage stage", "Status": "future",
                 "Description": "Triage follows Capture when category and contact details are present."},
                 delivery_lines[9], 10, delivery_source),
        proposal("working_agreement", {"Name": "Decisions logged within a day",
                 "Description": "Log decisions in the shared register within one business day.", "Status": "agreed"},
                 delivery_lines[10], 11, delivery_source),
        proposal("action_item", {"Name": "Confirm pilot staffing roster",
                 "Description": "Maya will confirm the pilot staffing roster.", "Target Date": "2026-10-01",
                 "Status": "committed", "Relationships": f"owned_by: {person_id}; addresses: {risk_id}"},
                 delivery_lines[11], 12, delivery_source),
        proposal("pain_point", {"Name": "Sample missing a description", "Status": "active"},
                 delivery_lines[12], 13, delivery_source),
    ]
    write_yaml(root / "workspace/.system/proposed-updates/workshop.yaml", {
        "source_refs": [source], "updates": updates,
    })
    print(f"Prepared synthetic review workspace: {root}")
    print(f"Pending proposals: {len(updates)} across {len({item['category'] for item in updates})} categories; accepted tracker rows: 2")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    prepare(root)
    if args.prepare_only:
        return 0
    result = subprocess.run([sys.executable, str(SCRIPTS / "review_server.py"),
                             "start", "--root", str(root)], capture_output=True, text=True)
    if result.returncode:
        print(result.stdout + result.stderr, file=sys.stderr)
        return result.returncode
    print(result.stdout.strip())
    for word in result.stdout.split():
        if word.startswith("http://127.0.0.1:"):
            webbrowser.open(word)
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
