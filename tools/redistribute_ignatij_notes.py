#!/usr/bin/env python3
"""Restore Ignatius' notes to the chapters containing their anchors.

The first note-separation release kept all 781 note bodies, but attached the
two source-page note tails to chapters 1 and 59.  Before the merged numeric
anchors were removed, commit ``2bfb8a9`` preserved an exact, gap-free 1..781
anchor sequence across 55 chapters.  This one-time migration applies that
verified map to the already-cleaned v3 book without changing any other field.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SOURCE_DIGEST = "b10c6b5c1d35921b5ae139f0a36a29dce34af624ea42b51d8ff6fff3a64f0e5b"
TARGET_DIGEST = "982312c60a4c10fca3a22d949126ed4ad67ec8cdc1499a430e385d26256c61ff"
EXPECTED_SOURCE_DISTRIBUTION = [(1, 37), (59, 744)]
EXPECTED_NOTE_COUNT = 781

# Derived from ``2bfb8a9:ignatij_prinoshenie.json`` (SHA-256
# 79aec2e5e1d1d6547aed7fe12f9ffe9efe75226fbcb888960ccddbb4b7a46a0c).
# Each tuple is an inclusive range of the original, globally numbered anchors.
NOTE_RANGES = {
    1: (1, 37),
    2: (38, 39),
    3: (40, 40),
    5: (41, 43),
    7: (44, 48),
    8: (49, 50),
    9: (51, 51),
    10: (52, 53),
    11: (54, 56),
    12: (57, 58),
    13: (59, 81),
    14: (82, 89),
    15: (90, 96),
    16: (97, 99),
    17: (100, 104),
    18: (105, 109),
    19: (110, 112),
    20: (113, 115),
    21: (116, 119),
    23: (120, 121),
    24: (122, 123),
    25: (124, 128),
    26: (129, 132),
    27: (133, 133),
    28: (134, 140),
    29: (141, 145),
    30: (146, 147),
    31: (148, 148),
    32: (149, 154),
    33: (155, 157),
    34: (158, 158),
    36: (159, 166),
    37: (167, 414),
    38: (415, 415),
    39: (416, 553),
    40: (554, 565),
    41: (566, 646),
    42: (647, 657),
    43: (658, 659),
    44: (660, 667),
    45: (668, 670),
    46: (671, 671),
    47: (672, 679),
    48: (680, 684),
    49: (685, 691),
    50: (692, 697),
    51: (698, 725),
    52: (726, 740),
    53: (741, 742),
    54: (743, 745),
    55: (746, 747),
    56: (748, 755),
    57: (756, 757),
    58: (758, 778),
    59: (779, 781),
}


def canonical_bytes(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def note_distribution(book: Mapping[str, Any]) -> list[tuple[int, int]]:
    return [
        (chapter["number"], len(chapter["notes"]))
        for chapter in book["chapters"]
        if chapter.get("notes")
    ]


def _validate_ranges(
    note_ranges: Mapping[int, tuple[int, int]],
    chapter_numbers: list[int],
    note_count: int,
) -> None:
    if list(note_ranges) != sorted(note_ranges):
        raise ValueError("Карта сносок должна идти по возрастанию глав")
    if any(chapter not in chapter_numbers for chapter in note_ranges):
        raise ValueError("Карта сносок ссылается на несуществующую главу")

    covered = [
        note_number
        for start, end in note_ranges.values()
        for note_number in range(start, end + 1)
    ]
    expected = list(range(1, note_count + 1))
    if covered != expected:
        raise ValueError(
            "Карта сносок не покрывает точную последовательность "
            f"1..{note_count}"
        )


def redistribute_notes(
    book: dict[str, Any],
    note_ranges: Mapping[int, tuple[int, int]],
    expected_source_distribution: list[tuple[int, int]],
    note_count: int,
) -> dict[str, Any]:
    """Redistribute notes while preserving their exact flattened sequence."""
    chapters = book.get("chapters")
    if not isinstance(chapters, list):
        raise ValueError("В книге нет списка chapters")

    chapter_numbers = [chapter.get("number") for chapter in chapters]
    if chapter_numbers != list(range(1, len(chapters) + 1)):
        raise ValueError("Нумерация глав должна быть непрерывной")
    if note_distribution(book) != expected_source_distribution:
        raise ValueError(
            "Неожиданное исходное распределение сносок: "
            f"{note_distribution(book)}"
        )

    notes = [
        note
        for chapter in chapters
        for note in chapter.get("notes", [])
    ]
    if len(notes) != note_count:
        raise ValueError(f"Ожидалось {note_count} сносок, найдено {len(notes)}")
    if any(not isinstance(note, str) or not note.strip() for note in notes):
        raise ValueError("Все сноски должны быть непустыми строками")

    _validate_ranges(note_ranges, chapter_numbers, note_count)
    by_number = {chapter["number"]: chapter for chapter in chapters}
    for chapter in chapters:
        chapter.pop("notes", None)
    for chapter_number, (start, end) in note_ranges.items():
        by_number[chapter_number]["notes"] = notes[start - 1:end]

    redistributed = [
        note
        for chapter in chapters
        for note in chapter.get("notes", [])
    ]
    if redistributed != notes:
        raise AssertionError("После миграции изменилась последовательность сносок")
    return book


def _without_migrated_fields(book: dict[str, Any]) -> dict[str, Any]:
    preserved = deepcopy(book)
    preserved.pop("version", None)
    for chapter in preserved["chapters"]:
        chapter.pop("notes", None)
    return preserved


def migrate_book(book: dict[str, Any]) -> dict[str, Any]:
    if book.get("id") != "ignatij_prinoshenie":
        raise ValueError("Миграция предназначена только для ignatij_prinoshenie")
    if book.get("version") != 3:
        raise ValueError(f"Ожидалась версия 3, найдена {book.get('version')}")
    if book.get("chapters_count") != 60 or len(book.get("chapters", [])) != 60:
        raise ValueError("Ожидалось 60 глав")

    preserved = _without_migrated_fields(book)
    redistribute_notes(
        book,
        NOTE_RANGES,
        EXPECTED_SOURCE_DISTRIBUTION,
        EXPECTED_NOTE_COUNT,
    )
    book["version"] = 4
    if _without_migrated_fields(book) != preserved:
        raise AssertionError("Миграция изменила поля кроме version и chapters[].notes")
    return book


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "ignatij_prinoshenie.json"
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_DIGEST:
        raise ValueError(f"Неожиданный исходный SHA-256: {digest}")

    migrated = canonical_bytes(migrate_book(json.loads(raw)))
    target_digest = hashlib.sha256(migrated).hexdigest()
    if target_digest != TARGET_DIGEST:
        raise AssertionError(f"Неожиданный итоговый SHA-256: {target_digest}")

    path.write_bytes(migrated)
    print(f"{path.name}: {len(migrated)} bytes, sha256={target_digest}")


if __name__ == "__main__":
    main()
