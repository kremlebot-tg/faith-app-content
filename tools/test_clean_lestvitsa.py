from copy import deepcopy
import json
from pathlib import Path
import unittest

from tools.clean_lestvitsa import MARKER_RE, clean_book


ROOT = Path(__file__).resolve().parents[1]


class CleanLestvitsaTest(unittest.TestCase):
    def test_removes_only_known_markers_and_preserves_structured_content(self) -> None:
        original = {
            "version": 2,
            "chapters": [
                {
                    "title": "О темнице11",
                    "paragraphs": [
                        "Первый текст12.",
                        "Вопрос?13",
                        "Запятая,14 продолжает фразу.",
                        "Точка с запятой;15 продолжает фразу.",
                        "Псалом 50 и глава 3.",
                    ],
                    "scripture_refs": [{"text": "Пс. 50", "url": "example"}],
                    "notes": ["Первая сноска.", "Вторая сноска."],
                    "test": [{"question": "Вопрос?"}],
                }
            ],
        }

        cleaned = clean_book(deepcopy(original), [11, 12, 13, 14, 15])

        self.assertEqual(cleaned["version"], 3)
        self.assertEqual(cleaned["chapters"][0]["title"], "О темнице")
        self.assertEqual(
            cleaned["chapters"][0]["paragraphs"],
            [
                "Первый текст.",
                "Вопрос?",
                "Запятая, продолжает фразу.",
                "Точка с запятой; продолжает фразу.",
                "Псалом 50 и глава 3.",
            ],
        )
        for field in ("scripture_refs", "notes", "test"):
            self.assertEqual(
                cleaned["chapters"][0][field], original["chapters"][0][field]
            )

    def test_rejects_unexpected_marker_sequence(self) -> None:
        book = {
            "version": 2,
            "chapters": [{"title": "Заголовок11", "paragraphs": []}],
        }

        with self.assertRaisesRegex(ValueError, "Неожиданная последовательность"):
            clean_book(book, [11, 12])

    def test_published_book_has_no_dangling_markers(self) -> None:
        book = json.loads(
            (ROOT / "ioann_lestvichnik.json").read_text(encoding="utf-8")
        )

        self.assertEqual(book["version"], 3)
        self.assertEqual(book["chapters_count"], 30)
        self.assertEqual(sum(len(chapter.get("notes", [])) for chapter in book["chapters"]), 124)
        self.assertEqual(
            sum(len(chapter.get("test", [])) for chapter in book["chapters"]), 90
        )
        for chapter in book["chapters"]:
            for text in [chapter["title"], *chapter["paragraphs"]]:
                self.assertIsNone(
                    MARKER_RE.search(text),
                    f"Слитая сноска в степени {chapter['number']}: {text[:80]}",
                )

        self.assertEqual(
            book["chapters"][4]["title"],
            "О попечительном и действительном покаянии и также о житии "
            "святых осужденников, и о темнице",
        )


if __name__ == "__main__":
    unittest.main()
