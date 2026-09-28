#!/usr/bin/env python3
"""Check workspace-add's three-document batch and per-document curation contract."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins" / "ascent" / "skills" / "workspace-add" / "SKILL.md"
SELECTOR = ROOT / "plugins" / "ascent" / "shared" / "scripts" / "select_inbox_batch.py"


def main() -> None:
    text = SKILL.read_text(encoding="utf-8")
    flat = " ".join(text.split())

    assert SELECTOR.is_file()
    assert "scripts/select_inbox_batch.py" in text
    assert "at most three original sources" in flat
    assert "never counts as a separate source" in flat
    assert "everything else stays in the inbox until its own batch" in flat
    assert "repeat until `selected` comes back empty" in flat
    assert "already selected earlier in this run, stop looping" in flat

    assert "one document per subagent, never grouped" in flat
    assert "group them by" not in flat
    assert "GPT Luna or Claude Haiku" in flat
    assert "high reasoning effort" in flat
    assert "Never claim a model or reasoning setting" in flat
    assert "curates each selected document itself, one at a time" in flat
    assert "curation ran without subagents" in flat

    assert "`basis` on every finding" in flat
    assert "Never propose an `inferred` finding as a stated fact" in flat
    assert "**Across documents**" in text
    assert "**Against existing tracker rows**" in text
    assert "**Against earlier batches in this run**" in text

    assert "mention the rest in Notes" not in flat
    assert "put its `proposal_id` in the link column" in flat
    assert "removes it if the row is rejected" in flat

    assert "must not move files" in flat
    assert "write to trackers" in flat
    assert "Nothing is written to the trackers here" in flat
    print("workspace-add batch curation contract: OK")


if __name__ == "__main__":
    main()
