#!/usr/bin/env python3
"""Regression tests for build_review_packet.py."""

from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
CONTENT_ROOT = TOOLS_DIR.parent
APP_ROOT = CONTENT_ROOT.parent / "faith_app"
GENERATED_DIR = CONTENT_ROOT / "reviews" / "v1.3.1"
MODULE_PATH = TOOLS_DIR / "build_review_packet.py"

SPEC = importlib.util.spec_from_file_location("build_review_packet", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BuildReviewPacketTest(unittest.TestCase):
    def test_excerpt_is_exact_prefix_and_word_bounded(self) -> None:
        paragraph = "Альфа бета гамма дельта"
        chapter = {"number": 1, "paragraphs": [paragraph]}
        excerpt = MODULE.source_excerpt(chapter, limit=17)
        self.assertEqual(excerpt, "Альфа бета гамма…")
        self.assertTrue(paragraph.startswith(excerpt[:-1]))
        self.assertEqual(chapter["paragraphs"][0], paragraph)

    def test_current_inputs_have_expected_coverage(self) -> None:
        books = MODULE.load_books(
            CONTENT_ROOT,
            APP_ROOT,
            "c" * 40,
            "a" * 40,
        )
        summary = {
            book.slug: (len(book.tested_chapters), book.question_count)
            for book in books
        }
        self.assertEqual(
            summary,
            {
                "lestvitsa": (30, 90),
                "feofan": (28, 84),
                "avva_dorofey": (21, 63),
            },
        )

    def test_render_is_byte_deterministic(self) -> None:
        kwargs = {
            "content_root": CONTENT_ROOT,
            "app_root": APP_ROOT,
            "content_commit": "c" * 40,
            "app_commit": "a" * 40,
        }
        first = MODULE.render_packet(**kwargs)
        second = MODULE.render_packet(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(
            sorted(first),
            [
                "00_README.md",
                "01_lestvitsa.md",
                "02_feofan.md",
                "03_avva_dorofey.md",
            ],
        )
        self.assertEqual(first["01_lestvitsa.md"].count("**Ключ:**"), 90)
        self.assertEqual(first["02_feofan.md"].count("**Ключ:**"), 84)
        self.assertEqual(first["03_avva_dorofey.md"].count("**Ключ:**"), 63)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            MODULE.write_packet(output, first)
            disk = {
                path.name: path.read_text(encoding="utf-8")
                for path in sorted(output.iterdir())
            }
        self.assertEqual(disk, first)

    def test_checked_in_packet_matches_generator(self) -> None:
        readme = (GENERATED_DIR / "00_README.md").read_text(encoding="utf-8")
        marker = re.search(
            r"build-review-packet: content=([0-9a-f]{40}) app=([0-9a-f]{40})",
            readme,
        )
        self.assertIsNotNone(marker)
        assert marker is not None
        rendered = MODULE.render_packet(
            content_root=CONTENT_ROOT,
            app_root=APP_ROOT,
            content_commit=marker.group(1),
            app_commit=marker.group(2),
        )
        actual = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted(GENERATED_DIR.glob("*.md"))
        }
        self.assertEqual(actual, rendered)


if __name__ == "__main__":
    unittest.main()
