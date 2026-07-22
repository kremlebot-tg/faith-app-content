#!/usr/bin/env python3
"""Remove known dangling footnote anchors from ``Что есть духовная жизнь``.

The notes were separated into ``chapters[].notes`` in release ``v1.0.2``, but
their numeric HTML anchors remained glued to words and punctuation in the main
text.  This one-time migration removes only the verified anchor sequence and
keeps notes, Scripture links, and all other structured content unchanged.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


SOURCE_DIGEST = "47a63edc0abcf74c671eaa749a8ffcb010ef6d9cc6b849cc9d5ea6436ee22920"
EXPECTED_MARKERS = list(range(1, 16))
# Scripture references use a thin space before a chapter and a comma before a
# verse.  Neither character is accepted here, so values such as ``Еф. 3, 16``
# cannot be mistaken for a footnote anchor.
MARKER_RE = re.compile(r"(?<=[А-Яа-яЁё»\)?!])(\d{1,2})(?!\d)")


def canonical_bytes(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def clean_book(
    book: dict[str, Any], expected_markers: list[int] = EXPECTED_MARKERS
) -> dict[str, Any]:
    markers: list[int] = []
    for chapter in book["chapters"]:
        texts = [chapter["title"], *chapter["paragraphs"]]
        cleaned: list[str] = []
        for text in texts:
            markers.extend(int(value) for value in MARKER_RE.findall(text))
            cleaned.append(MARKER_RE.sub("", text))
        chapter["title"] = cleaned[0]
        chapter["paragraphs"] = cleaned[1:]

    if markers != expected_markers:
        raise ValueError(
            "Неожиданная последовательность сносок: "
            f"ожидалось {expected_markers}, найдено {markers}"
        )
    if any(
        MARKER_RE.search(text)
        for chapter in book["chapters"]
        for text in [chapter["title"], *chapter["paragraphs"]]
    ):
        raise AssertionError("После очистки остались слитые цифровые маркеры")

    book["version"] = 3
    return book


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "feofan_dukhovnaja_zhizn.json"
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
