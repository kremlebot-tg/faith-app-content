from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from tools.clean_ignatij_prinoshenie import clean_book, marker_matches


ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_DIGEST = "b10c6b5c1d35921b5ae139f0a36a29dce34af624ea42b51d8ff6fff3a64f0e5b"


class CleanIgnatijPrinoshenieTest(unittest.TestCase):
    def test_removes_markers_after_words_and_punctuation_only(self) -> None:
        original = {
            "version": 2,
            "chapters": [
                {
                    "title": "Заголовок1",
                    "paragraphs": [
                        "Первый текст2. Дальше.3 Затем?4 Потом!5 И так;6, "
                        "иначе,7 и еще:8 Продолжение.",
                        "Ссылки (Мф.1 и Мф.2), (Ин.17:5) и (1Ин.1:8–10) "
                        "сохранятся.",
                    ],
                    "scripture_refs": [{"text": "Ин. 17:5", "url": "example"}],
                    "notes": [f"Сноска {number}." for number in range(1, 9)],
                    "test": [{"question": "Вопрос?"}],
                }
            ],
        }

        cleaned = clean_book(deepcopy(original), list(range(1, 9)))

        self.assertEqual(cleaned["version"], 3)
        self.assertEqual(cleaned["chapters"][0]["title"], "Заголовок")
        self.assertEqual(
            cleaned["chapters"][0]["paragraphs"],
            [
                "Первый текст. Дальше. Затем? Потом! И так;, иначе, и еще: "
                "Продолжение.",
                "Ссылки (Мф.1 и Мф.2), (Ин.17:5) и (1Ин.1:8–10) "
                "сохранятся.",
            ],
        )
        for field in ("scripture_refs", "notes", "test"):
            self.assertEqual(
                cleaned["chapters"][0][field], original["chapters"][0][field]
            )

    def test_rejects_missing_or_out_of_order_marker(self) -> None:
        book = {
            "version": 2,
            "chapters": [{"title": "Заголовок1", "paragraphs": ["Текст3"]}],
        }

        with self.assertRaisesRegex(
            ValueError, "Неожиданная последовательность"
        ):
            clean_book(book, [1, 2, 3])

    def test_published_book_has_exact_cleanup_and_preserves_all_notes(self) -> None:
        path = ROOT / "ignatij_prinoshenie.json"
        raw = path.read_bytes()
        book = json.loads(raw)

        self.assertEqual(hashlib.sha256(raw).hexdigest(), PUBLISHED_DIGEST)
        self.assertEqual(book["version"], 3)
        self.assertEqual(book["chapters_count"], 60)
        self.assertEqual(
            sum(len(chapter.get("notes", [])) for chapter in book["chapters"]),
            781,
        )
        self.assertEqual(
            [
                (chapter["number"], len(chapter["notes"]))
                for chapter in book["chapters"]
                if chapter.get("notes")
            ],
            [(1, 37), (59, 744)],
        )
        for chapter in book["chapters"]:
            for text in [chapter["title"], *chapter["paragraphs"]]:
                self.assertIsNone(
                    next(marker_matches(text), None),
                    f"Слитая сноска в главе {chapter['number']}: {text[:80]}",
                )

        by_number = {chapter["number"]: chapter for chapter in book["chapters"]}
        self.assertIn(
            "по свидетельству Святого Евангелия (Лк.\u200918:14)",
            " ".join(by_number[1]["paragraphs"]),
        )
        self.assertIn(
            "в письме к епископу Палладию: «Если тлят обычаи",
            " ".join(by_number[50]["paragraphs"]),
        )


if __name__ == "__main__":
    unittest.main()
