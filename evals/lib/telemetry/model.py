"""Shared data model for the run-record blocks the parsers emit.

Field names here are the wire names from `ascent.eval-run-record.v1` (see
docs/sgaf-717-evals-redesign-spec.md). Nothing in this module reads a log or
calls a model; it only shapes what the adapters found.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

RUN_RECORD_SCHEMA = "ascent.eval-run-record.v1"


@dataclass
class CostBlock:
    """Token counts and dollars for one run.

    `cache_read_tokens` and `cache_creation_tokens` are reported separately from
    `input_tokens` and priced separately, per the spec: folding them together
    makes a cache-heavy session look far more expensive than it is.
    `total_tokens` is the sum of all four, which is the figure the consistency
    verdict is computed from.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    estimated_usd: Optional[float] = None
    turns: int = 0
    tool_calls: int = 0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_creation_tokens
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "total_tokens": self.total_tokens,
            "estimated_usd": self.estimated_usd,
            "turns": self.turns,
            "tool_calls": self.tool_calls,
        }


@dataclass
class TimeBlock:
    """Wall clock, and a human baseline only when a human recorded one.

    `human_baseline_minutes` is never derived from the agent's own run. When it
    is None, `time_saved_minutes` and `speedup_factor` are omitted entirely
    rather than emitted as zero.
    """

    agent_wall_clock_seconds: Optional[float] = None
    human_baseline_minutes: Optional[float] = None
    human_baseline_source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"agent_wall_clock_seconds": self.agent_wall_clock_seconds}
        if self.human_baseline_minutes is None:
            return out
        out["human_baseline_minutes"] = self.human_baseline_minutes
        if self.human_baseline_source:
            out["human_baseline_source"] = self.human_baseline_source
        agent_minutes = (self.agent_wall_clock_seconds or 0.0) / 60.0
        out["time_saved_minutes"] = round(self.human_baseline_minutes - agent_minutes, 2)
        if agent_minutes > 0:
            out["speedup_factor"] = round(self.human_baseline_minutes / agent_minutes, 1)
        return out


@dataclass
class BehaviorBlock:
    """Calvin's two behaviour checks: did it call the skills, did it ask the questions."""

    skills_invoked: List[str] = field(default_factory=list)
    skills_expected: List[str] = field(default_factory=list)
    clarifying_questions_asked: int = 0
    clarifying_questions_required: List[str] = field(default_factory=list)

    @property
    def missing_skill_invocations(self) -> List[str]:
        invoked = set(self.skills_invoked)
        return [s for s in self.skills_expected if s not in invoked]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skills_invoked": list(self.skills_invoked),
            "skills_expected": list(self.skills_expected),
            "missing_skill_invocations": self.missing_skill_invocations,
            "clarifying_questions_asked": self.clarifying_questions_asked,
            "clarifying_questions_required": list(self.clarifying_questions_required),
        }


@dataclass
class SessionTelemetry:
    """Everything one adapter could determine from one session log."""

    host_name: str
    session_path: str
    telemetry_source: str
    cost: CostBlock
    time: TimeBlock
    behavior: BehaviorBlock
    host_version: Optional[str] = None
    models: List[str] = field(default_factory=list)
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    parse_stats: Dict[str, Any] = field(default_factory=dict)

    @property
    def model(self) -> Optional[str]:
        return self.models[0] if self.models else None

    def to_run_record(
        self,
        run_id: str,
        suite_id: str,
        arm: str,
        correctness: Optional[Dict[str, Any]] = None,
        human_baseline_minutes: Optional[float] = None,
        human_baseline_source: Optional[str] = None,
        skills_expected: Optional[List[str]] = None,
        clarifying_questions_required: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build an `ascent.eval-run-record.v1` document.

        Everything this parser cannot know deterministically has to be passed in:
        the correctness block comes from the correctness runner, and the human
        baseline comes from a human. Neither is invented here.
        """
        if skills_expected is not None:
            self.behavior.skills_expected = list(skills_expected)
        if clarifying_questions_required is not None:
            self.behavior.clarifying_questions_required = list(clarifying_questions_required)
        if human_baseline_minutes is not None:
            self.time.human_baseline_minutes = float(human_baseline_minutes)
            self.time.human_baseline_source = human_baseline_source

        record: Dict[str, Any] = {
            "schema_version": RUN_RECORD_SCHEMA,
            "run_id": run_id,
            "suite_id": suite_id,
            "arm": arm,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "host": {
                "name": self.host_name,
                "version": self.host_version,
                "model": self.model,
            },
        }
        if correctness is not None:
            record["correctness"] = correctness
        record["cost"] = self.cost.to_dict()
        record["time"] = self.time.to_dict()
        record["behavior"] = self.behavior.to_dict()
        record["provenance"] = {
            "telemetry_source": self.telemetry_source,
            "session_path": self.session_path,
            "extraction": "deterministic",
            "parse_stats": dict(self.parse_stats),
        }
        if len(self.models) > 1:
            record["provenance"]["models_seen"] = list(self.models)
        return record


def parse_iso8601(value: Any) -> Optional[_dt.datetime]:
    """Parse an ISO-8601 timestamp, tolerating the trailing `Z` and missing values.

    Returns None rather than raising, so one malformed timestamp in a session
    never takes down a whole parse.
    """
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return _dt.datetime.fromisoformat(text)
    except ValueError:
        return None


def to_iso8601_z(moment: Optional[_dt.datetime]) -> Optional[str]:
    """Render a datetime as the `...Z` form the spec's examples use."""
    if moment is None:
        return None
    if moment.tzinfo is not None:
        moment = moment.astimezone(_dt.timezone.utc).replace(tzinfo=None)
    return moment.replace(microsecond=0).isoformat() + "Z"
