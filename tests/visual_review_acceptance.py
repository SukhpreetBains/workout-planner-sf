#!/usr/bin/env python3
"""Run the visual review vertical-slice acceptance fixture."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "plugins" / "ascent" / "skills"


def main() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "plugins.ascent.shared.scripts.test_visual_review"],
        cwd=ROOT, text=True, capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(f"visual review acceptance failed:\n{result.stdout}\n{result.stderr}")

    app = SKILLS_ROOT / "review-updates" / "assets" / "review-app"
    required = [
        app / "index.html",
        app / "app.css",
        app / "app.js",
        app / "logo.svg",
        app / "vendor" / "anime.esm.min.js",
        app / "vendor" / "LICENSE.md",
        app / "fonts" / "slalom-sans-regular.woff2",
        app / "fonts" / "slalom-sans-bold.woff2",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"visual review assets missing: {', '.join(missing)}")
    css = (app / "app.css").read_text(encoding="utf-8")
    javascript = (app / "app.js").read_text(encoding="utf-8")
    html = (app / "index.html").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: reduce" in css
    assert "prefers-reduced-motion: reduce" in javascript
    assert 'role: "progressbar"' in javascript
    assert "Skip to review content" in html
    assert "aria-live=\"polite\"" in html
    print("Passed visual review acceptance fixture")


if __name__ == "__main__":
    main()
