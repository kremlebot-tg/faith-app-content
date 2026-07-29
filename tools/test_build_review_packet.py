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
HAS_APP_FIXTURES = all(
    (APP_ROOT / path).is_file()
    for path in (
        "assets/library/avva_dorofey.json",
        "assets/library/avva_dorofey_tests.json",
    )
)

SPEC = importlib.util.spec_from_file_location("build_review_packet", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


EXPLANATION = (
    "Объяснение связывает задание с содержанием главы и помогает осмысленно "
    "проверить понимание авторского наставления."
)


def mixed_questions() -> list[dict]:
    return [
        {
            "type": "choice",
            "question": "Какое утверждение передаёт смысл главы?",
            "answers": [
                {"text": "Первый содержательный ответ", "correct": False},
                {"text": "Второй содержательный ответ", "correct": True},
                {"text": "Третий содержательный ответ", "correct": False},
            ],
            "explanation": EXPLANATION,
        },
        {
            "type": "matching",
            "question": "Соотнесите образ и его смысл.",
            "pairs": [
                {"left": "Семя", "right": "Начало навыка"},
                {"left": "Корень", "right": "Устойчивая склонность"},
                {"left": "Плод", "right": "Видимый поступок"},
            ],
            "explanation": EXPLANATION,
        },
        {
            "type": "ordering",
            "question": "Восстановите последовательность рассуждения.",
            "items": ["Внимание", "Рассуждение", "Решение"],
            "explanation": EXPLANATION,
        },
        {
            "type": "cloze",
            "question": "Дополните краткое наставление.",
            "prompt": "Добрый навык требует ___.",
            "answers": [
                {"text": "внимания", "correct": True},
                {"text": "спешки", "correct": False},
            ],
            "explanation": EXPLANATION,
        },
    ]


class BuildReviewPacketTest(unittest.TestCase):
    def test_mixed_formats_render_with_one_shared_verdict(self) -> None:
        rendered = [
            "\n".join(MODULE._render_question(f"Т01.{index}", question))
            for index, question in enumerate(mixed_questions(), start=1)
        ]

        self.assertIn("- A. Первый содержательный ответ", rendered[0])
        self.assertIn("**Ключ:** B", rendered[0])
        self.assertIn("**Тип:** сопоставление", rendered[1])
        self.assertIn("- Семя → Начало навыка", rendered[1])
        self.assertIn("**Тип:** восстановление порядка", rendered[2])
        self.assertIn("1. Внимание", rendered[2])
        self.assertIn("3. Решение", rendered[2])
        self.assertIn("**Тип:** заполнение пропуска", rendered[3])
        self.assertIn(
            "**Фраза с пропуском:** Добрый навык требует ___.",
            rendered[3],
        )
        self.assertIn("**Ключ:** A", rendered[3])
        for body in rendered:
            self.assertEqual(body.count("**Ключ:**"), 1)
            self.assertEqual(body.count("**Вердикт:**"), 1)

    def test_review_validation_uses_common_mixed_schema(self) -> None:
        questions = mixed_questions()

        def book_with(tests: list[dict]) -> object:
            return MODULE.ReviewBook(
                slug="sample",
                filename="sample.md",
                prefix="Т",
                data={
                    "chapters_count": 1,
                    "chapters": [{"number": 1, "paragraphs": ["Текст."]}],
                },
                tests_by_chapter={1: tests},
                source_path=Path("sample.json"),
                test_path=None,
                repository="sample",
                commit="c" * 40,
                excluded_chapters=(),
                risk_tags={},
            )

        MODULE._validate_book(book_with(questions[:3]))
        MODULE._validate_book(book_with([questions[3], questions[1], questions[2]]))

        unknown = {
            "type": "mystery",
            "question": "Неизвестный формат.",
            "explanation": EXPLANATION,
        }
        with self.assertRaisesRegex(ValueError, "неизвестный тип задания"):
            MODULE._validate_book(book_with([unknown, questions[1], questions[2]]))

    def test_excerpt_is_exact_prefix_and_word_bounded(self) -> None:
        paragraph = "Альфа бета гамма дельта"
        chapter = {"number": 1, "paragraphs": [paragraph]}
        excerpt = MODULE.source_excerpt(chapter, limit=17)
        self.assertEqual(excerpt, "Альфа бета гамма…")
        self.assertTrue(paragraph.startswith(excerpt[:-1]))
        self.assertEqual(chapter["paragraphs"][0], paragraph)

    @unittest.skipUnless(
        HAS_APP_FIXTURES,
        "требуются приватные assets аввы Дорофея из соседнего faith_app",
    )
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

    @unittest.skipUnless(
        HAS_APP_FIXTURES,
        "требуются приватные assets аввы Дорофея из соседнего faith_app",
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

    @unittest.skipUnless(
        HAS_APP_FIXTURES,
        "требуются приватные assets аввы Дорофея из соседнего faith_app",
    )
    def test_checked_in_packet_matches_generator(self) -> None:
        readme = (GENERATED_DIR / "00_README.md").read_text(encoding="utf-8")
        marker = re.search(
            r"build-review-packet: content=([0-9a-f]{40}) app=([0-9a-f]{40})",
            readme,
        )
        self.assertIsNotNone(marker)
        assert marker is not None
        content_head = MODULE._git_head(CONTENT_ROOT)
        app_head = MODULE._git_head(APP_ROOT)
        if (marker.group(1), marker.group(2)) != (content_head, app_head):
            self.skipTest(
                "зафиксированный пакет нужно пересобрать после финальных "
                "app/content commits"
            )
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
