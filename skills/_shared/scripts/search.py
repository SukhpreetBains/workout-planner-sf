#!/usr/bin/env python3
"""Search the workspace: documents and tracker rows in one query.

Usage:
    py search.py "invoice approval delays"
    py search.py "salesforce" --kind system --limit 5
    py search.py --id PAIN-003

--kind filters to 'document' or a category (pain_point, stakeholder, ...).
--id prints one tracker row in full by its ID.
Run 'py sync.py' first if results look stale.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import SEARCH_DB


def snippet_query(con, query, kind, limit):
    sql = ("SELECT kind, ref, snippet(docs, 3, '>>', '<<', ' ... ', 24) "
           "FROM docs WHERE docs MATCH ?")
    params = [query]
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)
    return con.execute(sql, params).fetchall()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--kind")
    parser.add_argument("--id", dest="row_id")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if not SEARCH_DB.exists():
        print("no search index yet — run 'py sync.py' first")
        return 1
    con = sqlite3.connect(SEARCH_DB)

    if args.row_id:
        rows = con.execute("SELECT kind, content FROM docs WHERE ref = ?",
                           (args.row_id,)).fetchall()
        if not rows:
            print(f"no tracker row with ID {args.row_id}")
            return 1
        for kind, content in rows:
            print(f"[{kind}] {args.row_id}")
            print(content)
        return 0

    if not args.query:
        parser.print_help()
        return 1

    # quote each term so FTS5 treats hyphens/punctuation literally
    fts = " ".join(f'"{t}"' for t in args.query.split())
    try:
        results = snippet_query(con, fts, args.kind, args.limit)
    except sqlite3.OperationalError as exc:
        print(f"query error: {exc}")
        return 1
    if not results:
        print("no matches")
        return 0
    for kind, ref, snip in results:
        print(f"[{kind}] {ref}")
        print(f"    {' '.join(snip.split())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
