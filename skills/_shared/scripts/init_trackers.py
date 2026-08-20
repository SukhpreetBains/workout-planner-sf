#!/usr/bin/env python3
"""Create any missing tracker workbooks and tabs from the schema.

Usage:
    py init_trackers.py

Safe to run repeatedly: existing rows are never touched. Headers are only
rewritten on empty tabs.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trackers import init_trackers


def main() -> int:
    changed = init_trackers()
    if changed:
        for line in changed:
            print(line)
    else:
        print("trackers already match the schema — nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
