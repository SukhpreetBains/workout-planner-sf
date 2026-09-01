"""Deterministic detection for the `behavior` block: skills invoked, questions asked.

Calvin asked for two specific checks - "did it call all the skills it needs to
call?" and "did it ask the right questions it needs to ask to the user?" - so this
module answers exactly those two, with code and pattern matching only. No model
reads a transcript.

WHAT THIS DETECTS RELIABLY
--------------------------
Skills:
  * The `Skill` tool. `input.skill` is the skill name; plugin-scoped names
    (`superpowers:brainstorming`) and directory-scoped names (`apps/web:deploy`)
    are recorded verbatim, with the bare name also recorded as an alias so an
    `skills_expected` entry written without the prefix still matches.
  * Bash commands that touch a skills path with a name segment, e.g.
    `python3 skills/NAME/scripts/run.py` or `cat skills/NAME/SKILL.md`, including
    `.claude/skills/`, `.agent-framework/skills/` and absolute paths. Heredoc
    bodies are stripped before matching, so a command that writes a file
    *mentioning* a skills path is not scored as an invocation.

Questions:
  * The `AskUserQuestion` tool, which is the only structured "ask the user"
    channel. Each entry in `input.questions[]` counts as one question, and its
    `question` text is retained so a reviewer can check it against
    `clarifying_questions_required`.
  * Question-mark sentences in main-thread assistant `text` blocks, as a
    secondary signal.

WHERE IT IS WRONG, HONESTLY
---------------------------
* A skill whose instructions the agent follows *without* invoking the Skill tool
  or touching a `skills/` path is invisible here. Skills auto-loaded into context
  by a hook leave no tool-use trace at all.
* A Bash command that merely lists `skills/` (`ls skills/`) is counted as an
  invocation of nothing - the regex requires a name segment after `skills/` - but
  a command that reads one skill file while doing unrelated work is counted as an
  invocation of that skill. It cannot tell reading from executing.
* Heredoc bodies are stripped - including heredocs nested inside a quoted string
  with escaped newlines - because a command that *writes a file mentioning* a
  skills path is not an invocation of that skill. Stripping is deliberately
  slightly greedy: a real command that happens to contain a line starting with a
  prior heredoc delimiter loses the rest of that command from the scan. That
  errs toward *under*-counting invocations, which is the safer direction here -
  an under-count shows up as a false entry in `missing_skill_invocations`, which
  a reviewer investigates, whereas an over-count would quietly hide a genuine
  failure to call a skill.
* Even so, a skills path in an echoed string, a comment, or a `-c` program body
  outside a heredoc is still matched. At the level of shell text there is no
  difference between naming a path and using one.
* Question-mark counting is a heuristic and it over-counts. A rhetorical question
  in prose ("Why does this matter?") scores the same as a real ask. It is scoped
  to `text` blocks on the main thread - never `thinking` blocks, never subagent
  transcripts, since a subagent cannot reach the user - but that only bounds the
  error, it does not remove it. Treat `AskUserQuestion` as the trustworthy count
  (`questions.breakdown()["ask_user_question_tool"]`) and the total as an upper
  bound.
* Nothing here judges whether a question was the *right* question. Matching
  against `clarifying_questions_required` is a human or downstream-grader job;
  this module only supplies the text it found.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

SKILL_TOOL_NAMES = ("Skill",)
QUESTION_TOOL_NAMES = ("AskUserQuestion",)

_SKILL_PATH_RE = re.compile(
    r"(?:^|[\s'\"=:(<>|&;]|/)"          # start, separator, or path boundary
    r"(?:[\w./-]*/)?skills/"            # any prefix directory then skills/
    r"(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)"
    r"(?=[/\s'\"),;|&]|$)"              # must be followed by a path or word boundary
)

# Heredoc body, from `<<DELIM` to a line beginning with DELIM. The terminator
# only has to be followed by a boundary rather than end-of-line, because an
# agent writing a file from inside a quoted string leaves trailing quote and
# escape characters on the delimiter line.
_HEREDOC_RE = re.compile(
    r"<<-?\s*(?P<q>['\"]?)(?P<delim>[A-Za-z_][A-Za-z0-9_]*)(?P=q)"
    r".*?^(?P=delim)(?=[\s'\"\\)]|$)",
    re.DOTALL | re.MULTILINE,
)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`]*`")


def skills_in_tool_use(block: Dict[str, Any]) -> List[str]:
    """Skill names implied by one `tool_use` content block, in order.

    Split out of `SkillDetector` so a caller that needs to attribute *one* call
    to a skill - to time it, for instance - uses exactly the same matching rules
    as the session-level count, heredoc stripping included. Returns an empty list
    for a block that implies no skill, and carries every blind spot documented in
    this module's docstring.
    """
    found: List[str] = []

    def add(name: Optional[str]) -> None:
        if not isinstance(name, str):
            return
        name = name.strip()
        if name and name not in found:
            found.append(name)

    name = block.get("name")
    payload = block.get("input")
    if not isinstance(payload, dict):
        payload = {}

    if name in SKILL_TOOL_NAMES:
        skill = payload.get("skill")
        if isinstance(skill, str):
            add(skill)
            if ":" in skill:
                add(skill.rsplit(":", 1)[-1])
        return found

    if name == "Bash":
        command = payload.get("command")
        if isinstance(command, str):
            command = _HEREDOC_RE.sub(" ", command.replace("\\n", "\n"))
            for match in _SKILL_PATH_RE.finditer(command):
                candidate = match.group("name")
                if candidate in ("SKILL.md",) or candidate.startswith("*"):
                    continue
                add(candidate)
    return found


class SkillDetector:
    """Accumulates skill invocations across a session's tool-use blocks."""

    def __init__(self) -> None:
        self._ordered: List[str] = []
        self._seen: Set[str] = set()
        self._via_tool: List[str] = []
        self._via_bash: List[str] = []

    def _add(self, name: Optional[str], channel: str) -> None:
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name not in self._seen:
            self._seen.add(name)
            self._ordered.append(name)
        bucket = self._via_tool if channel == "tool" else self._via_bash
        if name not in bucket:
            bucket.append(name)

    def observe_tool_use(self, block: Dict[str, Any]) -> None:
        """Record any skill invocation implied by one `tool_use` content block."""
        name = block.get("name")
        payload = block.get("input")
        if not isinstance(payload, dict):
            payload = {}

        if name in SKILL_TOOL_NAMES:
            skill = payload.get("skill")
            if isinstance(skill, str):
                self._add(skill, "tool")
                if ":" in skill:
                    # Record the bare name too, so an expectation written
                    # without the plugin/directory prefix still matches.
                    self._add(skill.rsplit(":", 1)[-1], "tool")
            return

        if name == "Bash":
            command = payload.get("command")
            if isinstance(command, str):
                # Strip heredoc bodies first. A command that *writes a file*
                # mentioning `skills/<name>/...` is not an invocation of that
                # skill, and without this the detector reports whatever paths
                # happen to appear in generated content. Escaped newlines are
                # normalised first so a heredoc nested inside a quoted string
                # (common when an agent writes a file from within `python3 -c`)
                # is stripped too.
                command = _HEREDOC_RE.sub(" ", command.replace("\\n", "\n"))
                for match in _SKILL_PATH_RE.finditer(command):
                    candidate = match.group("name")
                    # A trailing file (SKILL.md) or a glob is not a skill name.
                    if candidate in ("SKILL.md",) or candidate.startswith("*"):
                        continue
                    self._add(candidate, "bash")

    def invoked(self) -> List[str]:
        """Skill names in first-invocation order."""
        return list(self._ordered)

    def breakdown(self) -> Dict[str, Any]:
        return {
            "via_skill_tool": list(self._via_tool),
            "via_bash_skills_path": list(self._via_bash),
            "detection": "pattern-based; see module docstring for known blind spots",
        }


class QuestionDetector:
    """Counts clarifying questions the agent put back to the user."""

    def __init__(self) -> None:
        self._tool_questions: List[str] = []
        self._text_questions: List[str] = []

    def observe_tool_use(self, block: Dict[str, Any], from_subagent: bool = False) -> None:
        if from_subagent:
            # A subagent has no channel to the user; its asks go to its parent.
            return
        if block.get("name") not in QUESTION_TOOL_NAMES:
            return
        payload = block.get("input")
        if not isinstance(payload, dict):
            return
        questions = payload.get("questions")
        if not isinstance(questions, list):
            return
        for entry in questions:
            if isinstance(entry, dict):
                text = entry.get("question") or entry.get("header") or ""
            elif isinstance(entry, str):
                text = entry
            else:
                text = ""
            self._tool_questions.append(str(text).strip())

    def observe_text(self, text: Optional[str], from_subagent: bool = False) -> None:
        """Count question-mark sentences in a main-thread assistant text block."""
        if from_subagent or not isinstance(text, str) or "?" not in text:
            return
        stripped = _INLINE_CODE_RE.sub(" ", _CODE_FENCE_RE.sub(" ", text))
        for sentence in _SENTENCE_SPLIT_RE.split(stripped):
            candidate = sentence.strip()
            if candidate.endswith("?") and len(candidate) > 1:
                self._text_questions.append(candidate)

    def total(self) -> int:
        """Total questions asked. Upper bound - see the module docstring."""
        return len(self._tool_questions) + len(self._text_questions)

    def breakdown(self) -> Dict[str, Any]:
        return {
            "ask_user_question_tool": len(self._tool_questions),
            "assistant_text_question_marks": len(self._text_questions),
            "ask_user_question_texts": list(self._tool_questions),
            "confidence": (
                "ask_user_question_tool is exact; assistant_text_question_marks is a "
                "heuristic upper bound that counts rhetorical questions too"
            ),
        }
