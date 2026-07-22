from copy import deepcopy
import json
from pathlib import Path
import unittest

from tools.clean_feofan_put import MARKER_RE, clean_book


ROOT = Path(__file__).resolve().parents[1]


class CleanFeofanPutTest(unittest.TestCase):
    def test_removes_known_markers_and_repairs_ocr(self) -> None:
        original = {
            "version": 2,
            "chapters": [
                {
                    "title": "Заголовок1",
                    "paragraphs": ["Первый текст2.", "До седин о6рящеши премудрость."],
                    "scripture_refs": [{"text": "Ин. 3:16", "url": "example"}],
                }
            ],
        }

        cleaned = clean_book(deepcopy(original), [1, 2], {})

        self.assertEqual(cleaned["version"], 3)
        self.assertEqual(cleaned["chapters"][0]["title"], "Заголовок")
        self.assertEqual(cleaned["chapters"][0]["paragraphs"], [
            "Первый текст.",
            "До седин обрящеши премудрость.",
        ])
        self.assertEqual(cleaned["chapters"][0]["scripture_refs"], original["chapters"][0]["scripture_refs"])

    def test_rejects_unexpected_marker_sequence(self) -> None:
        book = {
            "version": 2,
            "chapters": [
                {
                    "title": "Заголовок1",
                    "paragraphs": ["До седин о6рящеши премудрость."],
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "Неожиданная последовательность"):
            clean_book(book, [1, 2], {})

    def test_published_book_keeps_cleanup_and_liturgical_repairs(self) -> None:
        book = json.loads(
            (ROOT / "feofan_put_ko_spaseniyu.json").read_text(encoding="utf-8")
        )

        self.assertEqual(book["version"], 3)
        self.assertEqual(book["chapters_count"], 33)
        for chapter in book["chapters"]:
            for text in [chapter["title"], *chapter["paragraphs"]]:
                self.assertIsNone(
                    MARKER_RE.search(text),
                    f"Слитая сноска в главе {chapter['number']}: {text[:80]}",
                )

        by_number = {chapter["number"]: chapter for chapter in book["chapters"]}
        self.assertEqual(
            by_number[32]["paragraphs"],
            [
                "Православия наставниче, благочестия учителю и чистоты, "
                "Вышенский подвижниче, святителю Феофане Богомудре, писаньми "
                "твоими слово Божие изъяснил еси и всем верным путь ко спасению "
                "указал еси, моли Христа Бога спастися душам нашим."
            ],
        )
        self.assertEqual(
            by_number[33]["paragraphs"],
            [
                "Богоявлению тезоименитый, святителю Феофане, учении твоими "
                "многия люди просветил еси, со ангелы ныне предстоя Престолу "
                "Святыя Троицы, моли непрестанно о всех нас."
            ],
        )


if __name__ == "__main__":
    unittest.main()
