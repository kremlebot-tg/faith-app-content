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


def merge_drafts(
    root: Path,
    book_id: str,
    book_path: Path | None = None,
    excluded_chapters: dict[int, str] | None = None,
) -> Path:
    book_path = book_path or root / f"{book_id}.json"
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

    exclusions = excluded_chapters or {}
    overlap = set(by_number) & set(exclusions)
    if overlap:
        raise ValueError(
            f"Главы одновременно проверяются и исключены: {sorted(overlap)}"
        )
    accounted = set(by_number) | set(exclusions)
    if accounted != book_numbers:
        missing = sorted(book_numbers - accounted)
        extra = sorted(accounted - book_numbers)
        raise ValueError(
            f"Неполное покрытие {book_id}: пропущены={missing}, лишние={extra}"
        )

    output = {
        "book_id": book_id,
        "chapters": [by_number[number] for number in sorted(by_number)],
    }
    if exclusions:
        output["excluded_chapters"] = [
            {"number": number, "reason": exclusions[number]}
            for number in sorted(exclusions)
        ]
    output_path = root / "content_tests" / f"{book_id}.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", required=True)
    parser.add_argument(
        "--book-path",
        type=Path,
        help="Путь к JSON книги, если она встроена в приложение",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="NUMBER:REASON",
        help="Явно исключить структурную главу с непустой причиной",
    )
    args = parser.parse_args()
    exclusions: dict[int, str] = {}
    for value in args.exclude:
        number_text, separator, reason = value.partition(":")
        if not separator or not number_text.isdigit() or not reason.strip():
            parser.error("--exclude требует формат NUMBER:REASON")
        number = int(number_text)
        if number in exclusions:
            parser.error(f"глава {number} исключена дважды")
        exclusions[number] = reason.strip()
    path = merge_drafts(
        ROOT,
        args.book,
        args.book_path.resolve() if args.book_path else None,
        exclusions,
    )
    source = load(path)
    questions = sum(len(chapter["test"]) for chapter in source["chapters"])
    print(
        f"{path.name}: chapters={len(source['chapters'])} questions={questions}"
    )


if __name__ == "__main__":
    main()
