import unittest

from tools.prepare_release import validate_book


def sample_book() -> dict:
    return {
        "chapters_count": 2,
        "chapters": [
            {
                "number": 1,
                "kind": "section",
                "title": "Родительский раздел",
                "paragraphs": [],
                "scripture_refs": [],
            },
            {
                "number": 2,
                "title": "Содержательная глава",
                "paragraphs": ["Текст главы."],
                "scripture_refs": [],
            },
        ],
    }


class BookStructureTest(unittest.TestCase):
    def test_accepts_explicit_empty_section_and_readable_chapter(self) -> None:
        validate_book(sample_book(), "sample.json")

    def test_rejects_content_inside_section(self) -> None:
        book = sample_book()
        book["chapters"][0]["test"] = [{"question": "Лишний тест?"}]
        with self.assertRaisesRegex(ValueError, "Structural section contains"):
            validate_book(book, "sample.json")

    def test_rejects_empty_or_unknown_readable_node(self) -> None:
        empty = sample_book()
        empty["chapters"][1]["paragraphs"] = []
        with self.assertRaisesRegex(ValueError, "Empty readable chapter"):
            validate_book(empty, "sample.json")

        unknown = sample_book()
        unknown["chapters"][0]["kind"] = "heading"
        with self.assertRaisesRegex(ValueError, "Unknown chapter kind"):
            validate_book(unknown, "sample.json")


if __name__ == "__main__":
    unittest.main()
