from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from tools.clean_ignatij_prinoshenie import clean_book, marker_matches
from tools.redistribute_ignatij_notes import NOTE_RANGES, TARGET_DIGEST


ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_DIGEST = TARGET_DIGEST


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

    def test_published_book_has_cleanup_and_redistributed_notes(self) -> None:
        path = ROOT / "ignatij_prinoshenie.json"
        raw = path.read_bytes()
        book = json.loads(raw)

        self.assertEqual(hashlib.sha256(raw).hexdigest(), PUBLISHED_DIGEST)
        self.assertEqual(book["version"], 4)
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
            [
                (chapter, end - start + 1)
                for chapter, (start, end) in NOTE_RANGES.items()
            ],
        )
        for chapter in book["chapters"]:
            for text in [chapter["title"], *chapter["paragraphs"]]:
                self.assertIsNone(
                    next(marker_matches(text), None),
                    f"Слитая сноска в главе {chapter['number']}: {text[:80]}",
                )

        by_number = {chapter["number"]: chapter for chapter in book["chapters"]}
        self.assertEqual(
            by_number[1]["notes"][-1],
            "Алфавитный патерик и Достопамятные сказания, "
            "статья о авве Агафоне.",
        )
        self.assertEqual(
            by_number[2]["notes"][0],
            "Никифора Монашествующего слово. Добротолюбие, ч. 2.",
        )
        self.assertEqual(by_number[36]["notes"][-1], "Беседа 37.")
        self.assertTrue(
            by_number[37]["notes"][0].startswith(
                "Древнеобразное изложение преподобным Марком"
            )
        )
        self.assertEqual(
            by_number[59]["notes"],
            [
                "Алфавитный патерик, буква А.",
                "Образ изложения заимствован из евангельской притчи. Мф.\u200922:11.",
                "Образ изложения заимствован из евангельской притчи. Мф.\u200922:11.",
            ],
        )
        for chapter_number in (4, 6, 22, 35, 60):
            self.assertNotIn("notes", by_number[chapter_number])
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
