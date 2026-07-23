from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from tools.clean_feofan_put import clean_book, marker_matches


ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_DIGEST = "bb70c415b7c64a3b17d76fb84f72c62a2e83e145a7d3c5e449e8b147df5809c1"


class CleanFeofanPutTest(unittest.TestCase):
    def test_removes_markers_after_question_mark_and_full_stop_only(self) -> None:
        original = {
            "version": 3,
            "chapters": [
                {
                    "title": "Заголовок",
                    "paragraphs": [
                        "Почему не требовать отчета?79",
                        "Никто нас не учил этому».83",
                        "Ссылки (Флп.3:13), (1Кор. 9,24), гл.12 и пункт 79 "
                        "сохранятся.",
                    ],
                    "scripture_refs": [{"text": "Ин. 3:16", "url": "example"}],
                    "notes": ["Сноска сохранится."],
                    "test": [{"question": "Вопрос?"}],
                }
            ],
        }

        cleaned = clean_book(deepcopy(original), [79, 83])

        self.assertEqual(cleaned["version"], 4)
        self.assertEqual(cleaned["chapters"][0]["title"], "Заголовок")
        self.assertEqual(cleaned["chapters"][0]["paragraphs"], [
            "Почему не требовать отчета?",
            "Никто нас не учил этому».",
            "Ссылки (Флп.3:13), (1Кор. 9,24), гл.12 и пункт 79 "
            "сохранятся.",
        ])
        for field in ("scripture_refs", "notes", "test"):
            self.assertEqual(
                cleaned["chapters"][0][field], original["chapters"][0][field]
            )

    def test_rejects_unexpected_marker_sequence(self) -> None:
        book = {
            "version": 3,
            "chapters": [
                {
                    "title": "Заголовок",
                    "paragraphs": ["Текст?79", "Другой текст».83"],
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "Неожиданная последовательность"):
            clean_book(book, [79])

    def test_published_book_keeps_cleanup_and_liturgical_repairs(self) -> None:
        path = ROOT / "feofan_put_ko_spaseniyu.json"
        raw = path.read_bytes()
        book = json.loads(raw)

        self.assertEqual(hashlib.sha256(raw).hexdigest(), PUBLISHED_DIGEST)
        self.assertEqual(book["version"], 5)
        self.assertEqual(book["chapters_count"], 33)
        self.assertEqual(
            sum(len(chapter.get("test", [])) for chapter in book["chapters"]), 84
        )
        for chapter in book["chapters"]:
            for text in [chapter["title"], *chapter["paragraphs"]]:
                self.assertIsNone(
                    next(marker_matches(text), None),
                    f"Слитая сноска в главе {chapter['number']}: {text[:80]}",
                )

        by_number = {chapter["number"]: chapter for chapter in book["chapters"]}
        self.assertIn(
            "почему же не требовать от них отчета в том, что они слышали "
            "в дому Господнем?",
            " ".join(by_number[30]["paragraphs"]),
        )
        self.assertIn(
            "Ибо нельзя нам оправдаться и говорить: «Никто нас не учил "
            "этому».",
            " ".join(by_number[30]["paragraphs"]),
        )
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
