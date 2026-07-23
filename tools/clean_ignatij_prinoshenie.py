#!/usr/bin/env python3
"""Remove merged footnote anchors from Ignatius' ``Приношение``.

The release preparation split 781 note bodies into ``chapters[].notes`` but
left their numeric references glued to the main text.  This one-time migration
removes exactly the verified sequence 1..781.  Scripture references and every
structured field remain untouched.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterator, Match


SOURCE_DIGEST = "79aec2e5e1d1d6547aed7fe12f9ffe9efe75226fbcb888960ccddbb4b7a46a0c"
EXPECTED_MARKERS = list(range(1, 782))
CANDIDATE_RE = re.compile(
    r"(?<=[А-Яа-яЁё»”\)\]\.,;:?!])(\d{1,3})(?!\d)"
)
# Some old citations omit the thin space after a Biblical-book abbreviation,
# for example ``Пс.36:29`` or ``1Ин.1:8``.  Their chapter numbers are content,
# not footnote anchors.  The exact 1..781 sequence check below makes a new or
# ambiguous typography fail closed instead of silently changing the text.
DOTTED_ABBREVIATION_RE = re.compile(
    r"(?:^|[\s(])(?:[1-4])?"
    r"(?:Быт|Исх|Лев|Чис|Втор|Нав|Суд|Руф|Цар|Пар|Езд|Неем|Есф|"
    r"Иов|Пс|Притч|Еккл|Песн|Ис|Иер|Плач|Иез|Дан|Ос|Иоил|Ам|"
    r"Авд|Ион|Мих|Наум|Авв|Соф|Агг|Зах|Мал|Мф|Мк|Лк|Ин|Деян|"
    r"Иак|Пет|Иуд|Рим|Кор|Гал|Еф|Флп|Кол|Фес|Тим|Тит|Флм|Евр|"
    r"Откр)\.$"
)


def canonical_bytes(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def marker_matches(text: str) -> Iterator[Match[str]]:
    """Yield likely merged anchors, excluding recognised citation numbers."""
    for match in CANDIDATE_RE.finditer(text):
        prefix = text[:match.start()]
        if DOTTED_ABBREVIATION_RE.search(prefix):
            continue
        if prefix.endswith(":") and len(prefix) > 1 and prefix[-2].isdigit():
            continue
        yield match


def _remove_matches(text: str) -> str:
    parts: list[str] = []
    previous = 0
    for match in marker_matches(text):
        parts.append(text[previous:match.start()])
        previous = match.end()
    parts.append(text[previous:])
    return "".join(parts)


def clean_book(
    book: dict[str, Any], expected_markers: list[int] = EXPECTED_MARKERS
) -> dict[str, Any]:
    texts = [
        text
        for chapter in book["chapters"]
        for text in [chapter["title"], *chapter["paragraphs"]]
    ]
    markers = [
        int(match.group(1))
        for text in texts
        for match in marker_matches(text)
    ]
    if markers != expected_markers:
        raise ValueError(
            "Неожиданная последовательность сносок: "
            f"ожидалось {expected_markers}, найдено {markers}"
        )

    for chapter in book["chapters"]:
        chapter["title"] = _remove_matches(chapter["title"])
        chapter["paragraphs"] = [
            _remove_matches(paragraph) for paragraph in chapter["paragraphs"]
        ]

    if any(
        next(marker_matches(text), None) is not None
        for chapter in book["chapters"]
        for text in [chapter["title"], *chapter["paragraphs"]]
    ):
        raise AssertionError("После очистки остались слитые цифровые маркеры")
    book["version"] = 3
    return book


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "ignatij_prinoshenie.json"
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_DIGEST:
        raise ValueError(f"Неожиданный исходный SHA-256: {digest}")

    book = json.loads(raw)
    cleaned = canonical_bytes(clean_book(book))
    path.write_bytes(cleaned)
    print(
        f"{path.name}: {len(cleaned)} bytes, "
        f"sha256={hashlib.sha256(cleaned).hexdigest()}"
    )


if __name__ == "__main__":
    main()
