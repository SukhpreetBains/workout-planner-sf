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
    assert "**its own fresh** curation subagent" in flat
    assert "up to three at once" in flat
    assert "handles exactly one document in its lifetime" in flat
    assert "no follow-up or continuation messages to reuse it" in flat
    assert "Close each subagent once its result is back" in flat
    assert "The next batch gets new subagents" in flat
    assert "GPT Luna or Claude Haiku" in flat
    assert "high reasoning effort" in flat
    assert "Never claim a model or reasoning setting" in flat
    assert "curates each selected document itself, one at a time" in flat
    assert "curation ran without subagents" in flat

    five = "decisions, open questions, people, action items, and risks"
    assert flat.count(five) == 2, "meeting categories must be named in Step 2 and Step 4"
    assert "richest source for those three" not in flat
    assert "propose every follow-up that has an owner or a stated need to assign one" in flat
    assert "Fill `Target Date` whenever the source gives a calendar date" in flat
    assert "propose one `session` for every meeting processed" in flat
    assert "`Status: completed`" in flat

    assert "a heading or label alone is not evidence" in flat
    assert "Each excerpt must support the whole claim on its own" in flat
    assert "only when the source states an owner or a commitment" in flat
    assert "Never propose notes aimed at the presenter" in flat
    assert "A RACI becomes one `governance_rule` per activity" in flat
    assert "list the Consulted and Informed parties in the Description" in flat
    assert "Propose milestones whose date has passed like any others" in flat
    assert "in the handoff instead" not in flat
    assert "Do not merge or drop actions" in flat
    template = " ".join((SKILL.parent / "references" / "session-note-template.md").read_text(encoding="utf-8").split())
    assert "## Risks raised" in template
    assert "One line per distinct action in the source" in template

    assert "Propose a `person` only for a named individual" in flat
    assert "rather than recording the person as the role" in flat
    assert "Never propose the same person, team, or system twice under different categories" in flat
    authority = [
        "signed or executed documents over drafts and redlines",
        "later-dated documents over earlier ones",
        "delivery-phase documents (kickoff materials, meeting notes) over pre-sale ones",
    ]
    positions = [flat.index(rule) for rule in authority]
    assert positions == sorted(positions), "source authority order changed"
    assert "keep the signed value and propose an `open_question` naming both sources" in flat

    assert "`Name` is required in every category" in flat
    assert "a short summary of three to eight words written fresh" in flat
    assert "rather than copied or cut from the Description" in flat
    assert "validator fills it" not in flat

    assert "Caps, limits, and commercial terms are constraints" in flat
    assert "Excluded or deferred work is an `out_of_scope_item`" in flat
    assert "returns every stated fee, cap or limit, commercial term, scope inclusion and exclusion, dependency, and date as its own finding" in flat
    assert "Drop a candidate as superseded only after confirming the stronger source covers it" in flat
    assert "check the source's text yourself" in flat
    assert 'drop the candidate with the reason "not in <source>"' in flat
    assert "not a `requirement`" in flat
    assert "Internal Slalom commercial material stays out of the trackers" in flat
    assert "Commercial terms in a signed client agreement are client-agreed" in flat
    assert "Never set `completed`, `achieved`, `missed`, or `delivered` without a source saying so" in flat
    assert "date has passed with no source confirming the outcome" in flat
    assert "any documents filed without proposals and why" in flat

    assert "Build proposals from the subagents' findings" in flat
    assert "unless its subagent failed on it" in flat
    assert "Every candidate you drop needs a short reason" in flat
    assert "Never remove proposals in bulk by source document" in flat
    assert "dropped, grouped by reason" in flat

    assert "`basis` on every finding" in flat
    assert "Never propose an `inferred` finding as a stated fact" in flat
    assert "**Across documents**" in text
    assert "**Against existing tracker rows**" in text
    assert "**Against earlier batches in this run**" in text

    assert "mention the rest in Notes" not in flat
    assert "use its `proposal_id` as the ID" in flat
    assert "removes the relationship if it is rejected" in flat
    assert "Store each relationship once, on its source record" in flat
    assert "appearing in the same document is not one" in flat

    assert "classifies with the schema's definitions, not by keyword" in flat
    assert "apply the lookalike distinction the schema states" in flat
    assert "leave the rest empty for the reviewer" in flat
    assert "A finding whose category cannot be decided from the source is not proposed" in flat

    assert "must not move files" in flat
    assert "write to trackers" in flat
    assert "Nothing is written to the trackers here" in flat
    print("workspace-add batch curation contract: OK")


if __name__ == "__main__":
    main()
