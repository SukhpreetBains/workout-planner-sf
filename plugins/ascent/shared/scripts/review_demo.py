#!/usr/bin/env python3
"""Create and open a disposable, synthetic Opportunity review workspace.

Run: python3 plugins/ascent/shared/scripts/review_demo.py
Use --prepare-only to create the files without starting a browser or server.
Each run resets only a directory previously marked by this script. The default
directory is the operating system's temporary directory.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

SCRIPT = Path(__file__).resolve()
SCRIPTS = SCRIPT.parent
DEFAULT_ROOT = Path(tempfile.gettempdir()) / "ascent-workspace-review-demo"
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
             review: dict | None = None) -> dict:
    item = {
        "category": category,
        "action": action,
        "fields": fields,
        "source_refs": [source],
        "evidence": [{"source_ref": source, "excerpt": excerpt, "line_start": line}],
    }
    if tracker_id:
        item["id"] = tracker_id
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
                                     env={**os.environ, "ASCENT_OPPORTUNITY_ROOT": str(root)})
            if stopped.returncode:
                raise SystemExit(f"Could not stop the current demo server: {stopped.stderr.strip()}")
        shutil.rmtree(root)
    root.mkdir(parents=True)
    (root / MARKER).write_text("Synthetic workspace. Safe to reset with review_demo.py.\n", encoding="utf-8")
    for name in ("project", "trackers", "inbox", ".system"):
        (root / "workspace" / name).mkdir(parents=True, exist_ok=True)
    os.environ["ASCENT_OPPORTUNITY_ROOT"] = str(root)

    from trackers import init_trackers, upsert_row
    from paths import load_schema

    write_yaml(root / "workspace/.system/project.yaml", {
        "account": "Cedar Vale Cooperative (synthetic)",
        "opportunity": "Service Intake Modernization Demo",
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
        "A separate proposal intentionally lacks a required severity so designers can see the validation state.",
    ]
    delivery_path = root / delivery_source
    delivery_path.write_text("\n".join(delivery_lines) + "\n", encoding="utf-8")
    schema = load_schema()
    stakeholder_id = upsert_row("stakeholder", {
        "Name": "Maya Torres", "Role": "Service Operations Lead", "Influence": "high",
        "Source Refs": source,
    }, schema)
    system_id = upsert_row("system", {
        "Name": "QueueBoard", "System Type": "application", "Status": "active",
        "Description": "Fictional request tracking application", "Source Refs": source,
    }, schema)
    write_yaml(root / "workspace/.system/applied-updates/demo-stakeholder.yaml", {
        "source_refs": [source], "tracker_id": stakeholder_id,
        "review_decision": "accepted",
        "updates": [proposal("stakeholder", {"Name": "Maya Torres",
                              "Role": "Service Operations Lead", "Influence": "high"},
                             "Maya Torres owns service operations and approves intake process changes.",
                             3, source)],
    })
    write_yaml(root / "workspace/.system/rejected-updates/demo-out-of-scope.yaml", {
        "source_refs": [source], "review_decision": "rejected",
        "updates": [proposal("requirement", {"Statement": "Buy every intake tool on the market.",
                              "Requirement Type": "functional", "Status": "proposed"},
                             "The new intake flow must capture a request category before assignment.",
                             8, source)],
    })

    updates = [
        proposal("stakeholder", {"Role": "Service Operations Director",
                 "Engagement Notes": "Approves the regional pilot."},
                 "Maya Torres owns service operations and approves intake process changes.", 3,
                 source, action="update", tracker_id=stakeholder_id),
        proposal("system", {"Description": "Tracks requests in the current process and provides pilot exports."},
                 "QueueBoard is the current request tracking application.", 6, source,
                 action="update", tracker_id=system_id),
        proposal("pain_point", {"Statement": "Manual rekeying delays request assignment.",
                 "Pain Type": "process", "Severity": "high", "Status": "active",
                 "Quantified Impact": "Two business days for about 40 percent of requests",
                 "Raised By Stakeholder IDs": stakeholder_id},
                 "The rekeying step adds two business days to about 40 percent of requests.", 5, source),
        proposal("objective", {"Statement": "Assign 90 percent of requests within one business day.",
                 "Success Measure": "90 percent assigned within one business day",
                 "Priority": "high", "Status": "active"},
                 "Leadership wants 90 percent of requests assigned within one business day.", 7, source),
        proposal("requirement", {"Statement": "Capture a request category before assignment.",
                 "Requirement Type": "functional", "Priority": "must", "Status": "proposed"},
                 "The new intake flow must capture a request category before assignment.", 8, source),
        proposal("risk", {"Statement": "Pilot staffing may delay the rollout checkpoint.",
                 "Risk Title": "Pilot staffing", "Probability": 0.6, "Impact": "high",
                 "Status": "open", "Owner": "Maya Torres"},
                 "If the pilot team is unavailable, the rollout may miss its October checkpoint.", 9,
                 source),
        proposal("decision", {"Statement": "Pilot the new intake flow in one region first.",
                 "Status": "decided"},
                 "The team decided to pilot with one region before expanding.", 10, source),
        proposal("open_question", {"Question": "Who owns category definitions after the pilot?"},
                 "Who will own category definitions after the pilot?", 11, source,
                 review={"state": "flagged", "note": "Confirm an accountable owner."}),
        proposal("assumption", {"Statement": "Regional coordinators can spend four hours weekly on the pilot.",
                 "Status": "unvalidated", "Validation Plan": "Confirm with regional managers."},
                 delivery_lines[2], 3, delivery_source),
        proposal("issue", {"Statement": "A missing test environment blocks pilot rehearsal.",
                 "Status": "active", "Priority": "high"}, delivery_lines[3], 4, delivery_source),
        proposal("constraint", {"Statement": "Pilot support must stay within 120 hours.",
                 "Authority": "Signed pilot budget", "Constraint Type": "budget", "Status": "active"},
                 delivery_lines[4], 5, delivery_source),
        proposal("dependency", {"Statement": "The pilot rehearsal depends on a sandbox feed.",
                 "Owning Team": "Integration team", "Status": "open"},
                 delivery_lines[5], 6, delivery_source),
        proposal("session", {"Name": "Request category workshop", "Session Type": "workshop",
                 "Purpose": "Agree on pilot categories", "Scheduled Start": "2026-10-02",
                 "Owner Stakeholder IDs": stakeholder_id, "Status": "planned"},
                 delivery_lines[6], 7, delivery_source),
        proposal("operating_model", {"Name": "Pilot steering group", "Model Type": "governance",
                 "Decision Rights": "Pilot scope", "Accountable Stakeholder IDs": stakeholder_id,
                 "Status": "proposed"}, delivery_lines[7], 8, delivery_source),
        proposal("plan_item", {"Name": "Pilot rehearsal", "Plan Item Type": "milestone",
                 "End Date": "2026-10-15", "Status": "planned"},
                 delivery_lines[8], 9, delivery_source),
        proposal("workflow_stage", {"Workflow Name": "Request intake", "Stage Name": "Triage",
                 "Sequence": 2, "Entry Criteria": "Category and contact details present",
                 "Status": "draft"}, delivery_lines[9], 10, delivery_source),
        proposal("working_agreement", {"Statement": "Log decisions within one business day.",
                 "Agreement Type": "documentation", "Status": "agreed"},
                 delivery_lines[10], 11, delivery_source),
        proposal("action_item", {"Statement": "Confirm the pilot staffing roster.",
                 "Owner Stakeholder IDs": stakeholder_id, "Due Date": "2026-10-01",
                 "Status": "open"}, delivery_lines[11], 12, delivery_source),
        proposal("pain_point", {"Statement": "A second sample needs severity before acceptance.",
                 "Pain Type": "process", "Status": "active"},
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
