#!/usr/bin/env python3
"""Prove each high-value PPTX validator rule can fail."""

import argparse
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def rewrite_package(source, target, transform):
    with zipfile.ZipFile(source) as incoming, zipfile.ZipFile(target, "w") as outgoing:
        for info in incoming.infolist():
            data = incoming.read(info.filename)
            data = transform(info.filename, data)
            outgoing.writestr(info, data)


def run_validator(validator, deck, manifest):
    return subprocess.run(
        [sys.executable, str(validator), str(deck), "--manifest", str(manifest)],
        check=False,
        capture_output=True,
        text=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("deck", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    validator = Path(__file__).resolve().parents[1] / "validate_pptx.py"
    cases = [
        (
            "wrong font",
            "unapproved font",
            lambda name, data: data.replace(b"Avenir Next LT Pro", b"Arial") if name.startswith("ppt/slides/") else data,
        ),
        (
            "off-palette color",
            "outside the approved palette",
            lambda name, data: data.replace(b"0C62FB", b"FF00FF", 1) if name == "ppt/slides/slide1.xml" else data,
        ),
        (
            "missing expected copy",
            "missing expected native text",
            lambda name, data: data.replace(b"Customer-growth platform pilot", b"Customer platform pilot") if name == "ppt/slides/slide1.xml" else data,
        ),
        (
            "unresolved image",
            "image relationship does not resolve",
            lambda name, data: re.sub(rb'Target="\.\./media/[^"]+"', b'Target="../media/missing.png"', data, count=1)
            if name == "ppt/slides/_rels/slide1.xml.rels" else data,
        ),
        (
            "missing sources notes",
            "speaker notes do not contain a [Sources] block",
            lambda name, data: data.replace(b"[Sources]", b"[References]", 1) if name == "ppt/notesSlides/notesSlide2.xml" else data,
        ),
        (
            "wrong dimensions",
            "slide size is",
            lambda name, data: data.replace(b'cx="12191695"', b'cx="10000000"', 1) if name == "ppt/presentation.xml" else data,
        ),
        (
            "empty text slide",
            "has no native editable text",
            lambda name, data: re.sub(rb"<a:t>.*?</a:t>", b"", data, flags=re.DOTALL)
            if name == "ppt/slides/slide2.xml" else data,
        ),
    ]
    with tempfile.TemporaryDirectory(prefix="compose-validator-cases-") as temporary:
        temporary_path = Path(temporary)
        for index, (label, expected_error, transform) in enumerate(cases):
            broken = temporary_path / f"broken-{index}.pptx"
            rewrite_package(args.deck, broken, transform)
            result = run_validator(validator, broken, args.manifest)
            if result.returncode == 0:
                raise RuntimeError(f"{label} case passed unexpectedly")
            if expected_error not in result.stderr:
                raise RuntimeError(f"{label} case did not report {expected_error!r}:\n{result.stderr}")
    print(f"PASS: {len(cases)} deliberately broken PPTX validator cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
