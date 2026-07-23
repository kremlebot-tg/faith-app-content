#!/usr/bin/env python3
"""Проверка редакционной партии книжных тестов до полного покрытия книги."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

from audit_book_tests import audit_question


ROOT = Path(__file__).resolve().parent.parent


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_draft(path: Path) -> tuple[list[str], list[str], int, int]:
    errors: list[str] = []
    warnings: list[str] = []
    source = load(path)
    book_id = source.get("book_id")
    book_path = ROOT / f"{book_id}.json"
    if not isinstance(book_id, str) or not book_path.exists():
        return [f"{path.name}: не найдена книга {book_id!r}"], warnings, 0, 0

    book = load(book_path)
    book_numbers = {chapter["number"] for chapter in book["chapters"]}
    seen_numbers: set[int] = set()
    seen_prompts: dict[str, str] = {}
    correct_positions: list[int] = []
    question_count = 0

    for chapter in source.get("chapters", []):
        number = chapter.get("number")
        if not isinstance(number, int) or number not in book_numbers:
            errors.append(f"{path.name}: неизвестная глава {number!r}")
            continue
        if number in seen_numbers:
            errors.append(f"{path.name}: глава {number} повторяется")
        seen_numbers.add(number)
        tests = chapter.get("test", [])
        if len(tests) != 3:
            errors.append(
                f"{path.name}: глава {number} должна содержать ровно 3 вопроса"
            )
        for index, question in enumerate(tests, 1):
            question_count += 1
            location = f"{path.name}:глава {number}:вопрос {index}"
            normalized_prompt = question.get("question", "").strip().casefold()
            if normalized_prompt:
                previous = seen_prompts.get(normalized_prompt)
                if previous is not None:
                    errors.append(
                        f"{location}: вопрос повторяет формулировку из {previous}"
                    )
                else:
                    seen_prompts[normalized_prompt] = location
            correct_index = audit_question(
                question,
                location,
                errors,
                warnings,
            )
            if correct_index is not None:
                correct_positions.append(correct_index)

    if not seen_numbers:
        errors.append(f"{path.name}: редакционная партия не содержит глав")
    if correct_positions:
        distribution = Counter(correct_positions)
        counts = [distribution[index] for index in range(3)]
        if max(counts) - min(counts) > 1:
            errors.append(
                f"{path.name}: несбалансированы позиции верных ответов {counts}"
            )
    return errors, warnings, len(seen_numbers), question_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("draft", type=Path)
    args = parser.parse_args(argv)
    path = args.draft.resolve()
    errors, warnings, chapters, questions = audit_draft(path)
    print(
        f"draft={path.name} chapters={chapters} questions={questions} "
        f"errors={len(errors)} warnings={len(warnings)}"
    )
    for message in errors:
        print(f"ERROR {message}")
    for message in warnings:
        print(f"WARN  {message}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
