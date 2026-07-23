#!/usr/bin/env python3
"""Mark Feofan chapter 9 as a structural section without changing the text."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any


SOURCE_DIGEST = "638d1b134dc52f69d466a9b96ca796ed91e12638dfb629ffe48604d91666d835"
SECTION_NUMBER = 9
SECTION_TITLE = (
    "6. Восход до решимости оставить грех и посвятить себя богоугождению"
)


def canonical_bytes(data: object) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def mark_section(book: dict[str, Any]) -> dict[str, Any]:
    if book.get("id") != "feofan_put_ko_spaseniyu":
        raise ValueError("Неожиданный идентификатор книги")
    if book.get("version") != 4:
        raise ValueError(f"Ожидалась версия 4, найдена {book.get('version')}")
    if book.get("chapters_count") != 33 or len(book.get("chapters", [])) != 33:
        raise ValueError("Неожиданное число структурных элементов книги")

    original = deepcopy(book)
    matching = [
        chapter for chapter in book["chapters"]
        if chapter.get("number") == SECTION_NUMBER
    ]
    if len(matching) != 1:
        raise ValueError("Структурный заголовок 9 не найден однозначно")
    section = matching[0]
    if section.get("title") != SECTION_TITLE:
        raise ValueError("Неожиданный заголовок структурного раздела 9")
    if section.get("kind") is not None:
        raise ValueError("Тип структурного раздела уже задан")
    if section.get("paragraphs") != [] or section.get("scripture_refs") != []:
        raise ValueError("Структурный раздел 9 неожиданно содержит основной текст")
    if section.get("notes") or section.get("test") or section.get("attribution_note"):
        raise ValueError("Структурный раздел 9 неожиданно содержит вложенные данные")

    replacement: dict[str, Any] = {}
    for key, value in section.items():
        if key == "paragraphs":
            replacement["kind"] = "section"
        replacement[key] = value
    book["chapters"] = [
        replacement if chapter is section else chapter
        for chapter in book["chapters"]
    ]
    book["version"] = 5

    expected = deepcopy(book)
    expected["version"] = original["version"]
    expected_section = next(
        chapter for chapter in expected["chapters"]
        if chapter["number"] == SECTION_NUMBER
    )
    expected_section.pop("kind")
    if expected != original:
        raise AssertionError("Миграция изменила поля кроме version и chapters[9].kind")
    return book


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "feofan_put_ko_spaseniyu.json"
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_DIGEST:
        raise ValueError(f"Неожиданный исходный SHA-256: {digest}")
    updated = canonical_bytes(mark_section(json.loads(raw)))
    path.write_bytes(updated)
    print(
        f"{path.name}: {len(updated)} bytes, "
        f"sha256={hashlib.sha256(updated).hexdigest()}"
    )


if __name__ == "__main__":
    main()
