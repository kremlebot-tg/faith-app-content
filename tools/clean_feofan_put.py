#!/usr/bin/env python3
"""Remove known dangling footnote anchors from ``Путь ко спасению``."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


SOURCE_DIGEST = "8aa223232aaa3286646e6de659a60d644d4bd8d1ecc5b1feb708bd9c35c997f2"
EXPECTED_MARKERS = [*range(1, 79), 80, 81, 82]
MARKER_RE = re.compile(r"(?<=[А-Яа-яЁё»\)])(\d{1,3})(?!\d)")
LITURGICAL_REPAIRS = {
    (
        "Православия наставниче, благочестия учителю и чистоты, Вышенский "
        "подвижниче, святителю Феофане богомудре, писаниями твоими Слово "
        "Божие изъяснил еси и всем верным путь ко спасению указал еси, моли "
        "Христа Бога спастися душам нашим."
    ): (
        "Православия наставниче, благочестия учителю и чистоты, Вышенский "
        "подвижниче, святителю Феофане Богомудре, писаньми твоими слово "
        "Божие изъяснил еси и всем верным путь ко спасению указал еси, моли "
        "Христа Бога спастися душам нашим."
    ),
    (
        "Богоявлению тезоименитый, святителю Феофане, учениями твоими многия "
        "люди просветил еси, со ангелы ныне предстоя Престолы Святыя Троицы, "
        "моли непрестанно о всех нас."
    ): (
        "Богоявлению тезоименитый, святителю Феофане, учении твоими многия "
        "люди просветил еси, со ангелы ныне предстоя Престолу Святыя Троицы, "
        "моли непрестанно о всех нас."
    ),
}


def canonical_bytes(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def clean_book(
    book: dict[str, Any],
    expected_markers: list[int] = EXPECTED_MARKERS,
    liturgical_repairs: dict[str, str] = LITURGICAL_REPAIRS,
) -> dict[str, Any]:
    ocr_repairs = 0
    liturgical_counts = {source: 0 for source in liturgical_repairs}
    markers: list[int] = []
    for chapter in book["chapters"]:
        texts = [chapter["title"], *chapter["paragraphs"]]
        cleaned: list[str] = []
        for text in texts:
            ocr_repairs += text.count("о6рящеши")
            text = text.replace("о6рящеши", "обрящеши")
            for source, replacement in liturgical_repairs.items():
                liturgical_counts[source] += text.count(source)
                text = text.replace(source, replacement)
            markers.extend(int(value) for value in MARKER_RE.findall(text))
            cleaned.append(MARKER_RE.sub("", text))
        chapter["title"] = cleaned[0]
        chapter["paragraphs"] = cleaned[1:]

    if ocr_repairs != 1:
        raise ValueError(f"Ожидалось одно исправление «о6рящеши», найдено {ocr_repairs}")
    unexpected_liturgy = {
        source: count for source, count in liturgical_counts.items() if count != 1
    }
    if unexpected_liturgy:
        raise ValueError(
            f"Неожиданное число исправлений богослужебного текста: {unexpected_liturgy}"
        )
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
    path = root / "feofan_put_ko_spaseniyu.json"
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
