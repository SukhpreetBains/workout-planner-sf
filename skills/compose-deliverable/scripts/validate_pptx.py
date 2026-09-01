#!/usr/bin/env python3
"""Validate editable PPTX structure against a fixture-derived manifest."""

import argparse
import json
import posixpath
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree


DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PRESENTATION_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
RELATIONSHIP_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
EMU_PER_INCH = 914_400


def slide_number(name):
    match = re.search(r"slide(\d+)\.xml$", name)
    return int(match.group(1)) if match else sys.maxsize


def text_values(root):
    return [node.text or "" for node in root.findall(f".//{{{DRAWING_NS}}}t")]


def image_relationship_problems(archive, slide_name, names):
    problems = []
    slide_file = posixpath.basename(slide_name)
    rels_name = f"ppt/slides/_rels/{slide_file}.rels"
    if rels_name not in names:
        return problems
    root = ElementTree.fromstring(archive.read(rels_name))
    for relationship in root.findall(f".//{{{RELATIONSHIP_NS}}}Relationship"):
        if not relationship.get("Type", "").endswith("/image"):
            continue
        target = relationship.get("Target", "")
        if relationship.get("TargetMode") == "External" or re.match(r"^[a-z]+://", target, re.I):
            problems.append(f"{rels_name} contains an external image relationship: {target}")
            continue
        resolved = posixpath.normpath(posixpath.join("ppt/slides", target))
        if resolved not in names:
            problems.append(f"{rels_name} image relationship does not resolve: {target}")
    return problems


def notes_text(archive, slide_index, names):
    name = f"ppt/notesSlides/notesSlide{slide_index}.xml"
    if name not in names:
        return ""
    root = ElementTree.fromstring(archive.read(name))
    return " ".join(text_values(root))


def validate(deck_path, expected_text, manifest=None):
    problems = []
    if not deck_path.is_file():
        return [f"deck does not exist: {deck_path}"], {}
    try:
        archive = zipfile.ZipFile(deck_path)
    except (OSError, zipfile.BadZipFile) as error:
        return [f"not a readable PPTX package: {error}"], {}

    with archive:
        names = set(archive.namelist())
        for name in sorted({"[Content_Types].xml", "ppt/presentation.xml"} - names):
            problems.append(f"missing required package part: {name}")
        slide_names = sorted(
            (name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
            key=slide_number,
        )
        if not slide_names:
            problems.append("no slide XML parts found")

        expected_slides = manifest.get("slides", []) if manifest else []
        if manifest and len(slide_names) != len(expected_slides):
            problems.append(f"deck has {len(slide_names)} slides; manifest expects {len(expected_slides)}")
        if manifest:
            expected_numbers = list(range(1, len(expected_slides) + 1))
            manifest_numbers = [slide.get("number") for slide in expected_slides]
            if manifest_numbers != expected_numbers:
                problems.append("manifest slide numbers are not contiguous from 1")
            uncovered = [section["index"] for section in manifest.get("sections", []) if not section.get("slideNumbers")]
            if uncovered:
                problems.append(f"manifest does not cover source section(s): {', '.join(map(str, uncovered))}")

        all_text = []
        native_shapes = 0
        pictures = 0
        expected_font = manifest.get("font") if manifest else None
        allowed_colors = set(manifest.get("allowedColors", [])) if manifest else set()
        classification = manifest.get("classification") if manifest else None

        for index, name in enumerate(slide_names, start=1):
            root = ElementTree.fromstring(archive.read(name))
            texts = text_values(root)
            combined = " ".join(texts)
            all_text.extend(texts)
            slide_shapes = len(root.findall(f".//{{{PRESENTATION_NS}}}sp"))
            slide_pictures = len(root.findall(f".//{{{PRESENTATION_NS}}}pic"))
            native_shapes += slide_shapes
            pictures += slide_pictures
            slide_manifest = expected_slides[index - 1] if index <= len(expected_slides) else {}

            if slide_manifest.get("requiresNativeText", True) and not any(text.strip() for text in texts):
                problems.append(f"{name} has no native editable text")
            if slide_manifest.get("requiresNativeShapes", True) and slide_shapes == 0:
                problems.append(f"{name} has no native PowerPoint shapes")
            if slide_manifest.get("requiresLogo") and slide_pictures == 0:
                problems.append(f"{name} has no packaged logo image")

            for phrase in [*slide_manifest.get("expectedText", []), *slide_manifest.get("expectedSourceLabels", [])]:
                if phrase not in combined:
                    problems.append(f"{name} is missing expected native text: {phrase!r}")
            if classification and classification not in combined:
                problems.append(f"{name} is missing the classification/footer text")

            declared_fonts = {
                node.get("typeface") for node in root.findall(f".//*[@typeface]") if node.get("typeface")
            }
            if expected_font and expected_font not in declared_fonts:
                problems.append(f"{name} does not declare the approved PowerPoint font {expected_font!r}")
            unexpected_fonts = sorted(font for font in declared_fonts if expected_font and font != expected_font)
            if unexpected_fonts:
                problems.append(f"{name} declares unapproved font(s): {', '.join(unexpected_fonts)}")

            if allowed_colors:
                slide_colors = {
                    node.get("val", "").upper()
                    for node in root.findall(f".//{{{DRAWING_NS}}}srgbClr")
                    if node.get("val")
                }
                unapproved = sorted(slide_colors - allowed_colors)
                if unapproved:
                    problems.append(f"{name} contains color(s) outside the approved palette: {', '.join(unapproved)}")

            problems.extend(image_relationship_problems(archive, name, names))
            if slide_manifest.get("requiresSourcesNotes") and "[Sources]" not in notes_text(archive, index, names):
                problems.append(f"{name} speaker notes do not contain a [Sources] block")

        combined_text = " ".join(all_text)
        for phrase in expected_text:
            if phrase not in combined_text:
                problems.append(f"expected native text is absent: {phrase!r}")
        if native_shapes == 0:
            problems.append("no native PowerPoint shapes found; raster-only output is not acceptable")

        if manifest and "ppt/presentation.xml" in names:
            root = ElementTree.fromstring(archive.read("ppt/presentation.xml"))
            size = root.find(f".//{{{PRESENTATION_NS}}}sldSz")
            if size is None:
                problems.append("presentation slide size is absent")
            else:
                width = int(size.get("cx", "0")) / EMU_PER_INCH
                height = int(size.get("cy", "0")) / EMU_PER_INCH
                expected_size = manifest.get("slideSize", {})
                if abs(width - expected_size.get("widthInches", width)) > 0.002 or abs(height - expected_size.get("heightInches", height)) > 0.002:
                    problems.append(
                        f"slide size is {width:.3f} x {height:.3f} in; expected "
                        f"{expected_size.get('widthInches')} x {expected_size.get('heightInches')} in"
                    )
                if expected_size.get("orientation") == "landscape" and width <= height:
                    problems.append("slide orientation is not landscape")

        stats = {
            "slides": len(slide_names),
            "native_text_runs": len([text for text in all_text if text.strip()]),
            "native_shapes": native_shapes,
            "pictures": pictures,
        }
        return problems, stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("deck", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expect-text", action="append", default=[])
    args = parser.parse_args()
    manifest = None
    if args.manifest:
        try:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(f"FAIL: cannot read manifest: {error}", file=sys.stderr)
            return 1

    problems, stats = validate(args.deck, args.expect_text, manifest)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print(
        "PASS: editable PPTX structure "
        f"({stats['slides']} slides, {stats['native_text_runs']} text runs, "
        f"{stats['native_shapes']} shapes, {stats['pictures']} pictures)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
