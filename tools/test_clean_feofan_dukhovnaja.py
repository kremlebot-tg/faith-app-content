from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from tools.clean_feofan_dukhovnaja import MARKER_RE, clean_book


ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_DIGEST = "779cecfe2039f3e74e76010995cc4acb45ae07099c5784a329eda22b0acf809a"


class CleanFeofanDukhovnajaTest(unittest.TestCase):
    def test_removes_only_known_markers_and_preserves_structured_content(self) -> None:
        original = {
            "version": 2,
            "chapters": [
                {
                    "title": "Письмо1",
                    "paragraphs": [
                        "Святого Андрея2. Ссылка (Еф.\u20093,\u200916) сохранится.",
                        "Поворотила?3 Вот что было дальше.",
                        "Помните гувернантку!4 Она ждала.",
                        "Смотри пункт 26 и том 2.",
                    ],
                    "scripture_refs": [{"text": "Еф. 3:16", "url": "example"}],
                    "notes": ["Первая сноска.", "Вторая сноска."],
                    "test": [{"question": "Вопрос?"}],
                }
            ],
        }

        cleaned = clean_book(deepcopy(original), [1, 2, 3, 4])

        self.assertEqual(cleaned["version"], 3)
        self.assertEqual(cleaned["chapters"][0]["title"], "Письмо")
        self.assertEqual(
            cleaned["chapters"][0]["paragraphs"],
            [
                "Святого Андрея. Ссылка (Еф.\u20093,\u200916) сохранится.",
                "Поворотила? Вот что было дальше.",
                "Помните гувернантку! Она ждала.",
                "Смотри пункт 26 и том 2.",
            ],
        )
        for field in ("scripture_refs", "notes", "test"):
            self.assertEqual(
                cleaned["chapters"][0][field], original["chapters"][0][field]
            )

    def test_rejects_unexpected_marker_sequence(self) -> None:
        book = {
            "version": 2,
            "chapters": [{"title": "Письмо1", "paragraphs": []}],
        }

        with self.assertRaisesRegex(
            ValueError, "Неожиданная последовательность"
        ):
            clean_book(book, [1, 2])

    def test_published_book_has_exact_cleanup_and_preserves_notes(self) -> None:
        path = ROOT / "feofan_dukhovnaja_zhizn.json"
        raw = path.read_bytes()
        book = json.loads(raw)

        self.assertEqual(hashlib.sha256(raw).hexdigest(), PUBLISHED_DIGEST)
        self.assertEqual(book["version"], 3)
        self.assertEqual(book["chapters_count"], 80)
        self.assertEqual(
            sum(len(chapter.get("notes", [])) for chapter in book["chapters"]), 15
        )
        self.assertEqual(
            [
                chapter["number"]
                for chapter in book["chapters"]
                if chapter.get("notes")
            ],
            [14, 28, 37, 39, 43, 45, 51, 52, 65, 69, 74],
        )
        for chapter in book["chapters"]:
            for text in [chapter["title"], *chapter["paragraphs"]]:
                self.assertIsNone(
                    MARKER_RE.search(text),
                    f"Слитая сноска в письме {chapter['number']}: {text[:80]}",
                )

        by_number = {chapter["number"]: chapter for chapter in book["chapters"]}
        self.assertIn("святого Андрея. Но у небожителей", by_number[14]["paragraphs"][0])
        self.assertIn("притче о мнасах (", by_number[28]["paragraphs"][1])
        self.assertIn("всякая душа издает свой запах (2Кор.\u20092,15)", by_number[51]["paragraphs"][2])
        self.assertIn("Помните гувернантку! Она семь лет ждала", by_number[74]["paragraphs"][6])


if __name__ == "__main__":
    unittest.main()
