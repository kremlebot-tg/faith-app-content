from copy import deepcopy
import unittest

from tools.redistribute_ignatij_notes import (
    migrate_book,
    note_distribution,
    redistribute_notes,
)


def sample_book() -> dict:
    return {
        "id": "sample",
        "version": 3,
        "chapters_count": 4,
        "chapters": [
            {
                "number": 1,
                "title": "Первая",
                "paragraphs": ["Текст 1"],
                "scripture_refs": [{"text": "Мф. 1:1", "url": "example"}],
                "notes": ["Сноска 1"],
            },
            {
                "number": 2,
                "title": "Вторая",
                "paragraphs": ["Текст 2"],
                "scripture_refs": [],
            },
            {
                "number": 3,
                "title": "Третья",
                "paragraphs": ["Текст 3"],
                "scripture_refs": [],
            },
            {
                "number": 4,
                "title": "Четвертая",
                "paragraphs": ["Текст 4"],
                "scripture_refs": [],
                "notes": ["Сноска 2", "Сноска 3", "Сноска 4"],
                "test": [{"question": "Вопрос?"}],
            },
        ],
    }


def without_notes(book: dict) -> dict:
    cleaned = deepcopy(book)
    for chapter in cleaned["chapters"]:
        chapter.pop("notes", None)
    return cleaned


class RedistributeIgnatijNotesTest(unittest.TestCase):
    def test_redistributes_without_changing_other_fields(self) -> None:
        original = sample_book()
        migrated = redistribute_notes(
            deepcopy(original),
            {1: (1, 1), 2: (2, 3), 4: (4, 4)},
            [(1, 1), (4, 3)],
            4,
        )

        self.assertEqual(note_distribution(migrated), [(1, 1), (2, 2), (4, 1)])
        self.assertEqual(migrated["chapters"][0]["notes"], ["Сноска 1"])
        self.assertEqual(
            migrated["chapters"][1]["notes"],
            ["Сноска 2", "Сноска 3"],
        )
        self.assertNotIn("notes", migrated["chapters"][2])
        self.assertEqual(migrated["chapters"][3]["notes"], ["Сноска 4"])
        self.assertEqual(without_notes(migrated), without_notes(original))

    def test_rejects_range_map_with_a_gap(self) -> None:
        with self.assertRaisesRegex(ValueError, "не покрывает"):
            redistribute_notes(
                sample_book(),
                {1: (1, 1), 2: (3, 4)},
                [(1, 1), (4, 3)],
                4,
            )

    def test_rejects_unexpected_source_distribution(self) -> None:
        with self.assertRaisesRegex(ValueError, "исходное распределение"):
            redistribute_notes(
                sample_book(),
                {1: (1, 1), 2: (2, 3), 4: (4, 4)},
                [(1, 4)],
                4,
            )

    def test_rejects_empty_note(self) -> None:
        book = sample_book()
        book["chapters"][3]["notes"][1] = " "
        with self.assertRaisesRegex(ValueError, "непустыми строками"):
            redistribute_notes(
                book,
                {1: (1, 1), 2: (2, 3), 4: (4, 4)},
                [(1, 1), (4, 3)],
                4,
            )

    def test_book_migration_rejects_wrong_identity_or_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "только для ignatij"):
            migrate_book(sample_book())

        book = sample_book()
        book["id"] = "ignatij_prinoshenie"
        book["version"] = 4
        with self.assertRaisesRegex(ValueError, "Ожидалась версия 3"):
            migrate_book(book)


if __name__ == "__main__":
    unittest.main()
