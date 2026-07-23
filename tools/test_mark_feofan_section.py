from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from tools.mark_feofan_section import SECTION_TITLE, mark_section


ROOT = Path(__file__).resolve().parents[1]


def sample_book() -> dict:
    return {
        "id": "feofan_put_ko_spaseniyu",
        "version": 4,
        "chapters_count": 33,
        "chapters": [
            {
                "number": number,
                "title": SECTION_TITLE if number == 9 else f"Глава {number}",
                "paragraphs": [] if number == 9 else [f"Текст {number}"],
                "scripture_refs": [],
                **({"test": [{"question": "Вопрос?"}]} if number == 10 else {}),
            }
            for number in range(1, 34)
        ],
    }


class MarkFeofanSectionTest(unittest.TestCase):
    def test_marks_only_the_structural_heading(self) -> None:
        original = sample_book()
        updated = mark_section(deepcopy(original))

        self.assertEqual(updated["version"], 5)
        by_number = {chapter["number"]: chapter for chapter in updated["chapters"]}
        self.assertEqual(by_number[9]["kind"], "section")
        self.assertEqual(by_number[9]["paragraphs"], [])
        self.assertEqual(by_number[10], original["chapters"][9])

        restored = deepcopy(updated)
        restored["version"] = 4
        next(ch for ch in restored["chapters"] if ch["number"] == 9).pop("kind")
        self.assertEqual(restored, original)

    def test_rejects_text_or_wrong_source_version(self) -> None:
        with_text = sample_book()
        with_text["chapters"][8]["paragraphs"] = ["Неожиданный текст"]
        with self.assertRaisesRegex(ValueError, "содержит основной текст"):
            mark_section(with_text)

        wrong_version = sample_book()
        wrong_version["version"] = 5
        with self.assertRaisesRegex(ValueError, "Ожидалась версия 4"):
            mark_section(wrong_version)

    def test_published_book_has_one_explicit_section(self) -> None:
        raw = (ROOT / "feofan_put_ko_spaseniyu.json").read_bytes()
        book = json.loads(raw)
        sections = [
            chapter for chapter in book["chapters"]
            if chapter.get("kind") == "section"
        ]

        self.assertEqual(book["version"], 5)
        self.assertEqual([chapter["number"] for chapter in sections], [9])
        self.assertEqual(sections[0]["title"], SECTION_TITLE)
        self.assertEqual(sections[0]["paragraphs"], [])
        self.assertEqual(
            sum(chapter.get("kind") != "section" for chapter in book["chapters"]),
            32,
        )
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "bb70c415b7c64a3b17d76fb84f72c62a2e83e145a7d3c5e449e8b147df5809c1",
        )


if __name__ == "__main__":
    unittest.main()
