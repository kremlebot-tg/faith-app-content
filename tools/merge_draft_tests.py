#!/usr/bin/env python3
"""Собрать проверенные редакционные партии в единый файл авторских тестов."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def merge_drafts(root: Path, book_id: str) -> Path:
    book_path = root / f"{book_id}.json"
    if not book_path.exists():
        raise ValueError(f"Не найдена книга: {book_path}")
    book = load(book_path)
    book_numbers = {chapter["number"] for chapter in book["chapters"]}

    drafts = sorted((root / "content_tests" / "drafts").glob(f"{book_id}_*.json"))
    if not drafts:
        raise ValueError(f"Не найдены редакционные партии для {book_id}")

    by_number: dict[int, dict[str, Any]] = {}
    for path in drafts:
        source = load(path)
        if source.get("book_id") != book_id:
            raise ValueError(f"Неверный book_id в {path.name}")
        for chapter in source.get("chapters", []):
            number = chapter.get("number")
            if not isinstance(number, int):
                raise ValueError(f"Некорректный номер главы в {path.name}: {number!r}")
            if number in by_number:
                raise ValueError(f"Глава {number} повторяется в редакционных партиях")
            by_number[number] = chapter

    if set(by_number) != book_numbers:
        missing = sorted(book_numbers - set(by_number))
        extra = sorted(set(by_number) - book_numbers)
        raise ValueError(
            f"Неполное покрытие {book_id}: пропущены={missing}, лишние={extra}"
        )

    output = {
        "book_id": book_id,
        "chapters": [by_number[number] for number in sorted(by_number)],
    }
    output_path = root / "content_tests" / f"{book_id}.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", required=True)
    args = parser.parse_args()
    path = merge_drafts(ROOT, args.book)
    source = load(path)
    questions = sum(len(chapter["test"]) for chapter in source["chapters"])
    print(
        f"{path.name}: chapters={len(source['chapters'])} questions={questions}"
    )


if __name__ == "__main__":
    main()
