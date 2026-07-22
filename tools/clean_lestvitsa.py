#!/usr/bin/env python3
"""Remove known dangling footnote anchors from ``Лествица``.

The notes were already separated into ``chapters[].notes`` during the first
content release, but the numeric HTML anchors remained glued to words in the
main text.  This migration only removes the verified anchor sequence and keeps
the notes, Scripture links, and embedded tests byte-for-byte equivalent as
JSON values.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


SOURCE_DIGEST = "e96a754c48500df72de1078c56355d8a5c374f5ca559d7b922accf7dd563b75f"
EXPECTED_MARKERS = list(range(11, 135))
MARKER_RE = re.compile(r"(?<=[А-Яа-яЁё»\),;?])(\d{1,3})(?!\d)")
PUNCTUATION_REPAIR = ("благочестивее поступил?.", "благочестивее поступил?")


def canonical_bytes(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def clean_book(
    book: dict[str, Any], expected_markers: list[int] = EXPECTED_MARKERS
) -> dict[str, Any]:
    markers: list[int] = []
    punctuation_repairs = 0
    for chapter in book["chapters"]:
        texts = [chapter["title"], *chapter["paragraphs"]]
        cleaned: list[str] = []
        for text in texts:
            markers.extend(int(value) for value in MARKER_RE.findall(text))
            text = MARKER_RE.sub("", text)
            punctuation_repairs += text.count(PUNCTUATION_REPAIR[0])
            cleaned.append(text.replace(*PUNCTUATION_REPAIR))
        chapter["title"] = cleaned[0]
        chapter["paragraphs"] = cleaned[1:]

    if markers != expected_markers:
        raise ValueError(
            "Неожиданная последовательность сносок: "
            f"ожидалось {expected_markers}, найдено {markers}"
        )
    if expected_markers == EXPECTED_MARKERS and punctuation_repairs != 1:
        raise ValueError(
            "Неожиданное число исправлений двойной пунктуации: "
            f"{punctuation_repairs}"
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
    path = root / "ioann_lestvichnik.json"
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
