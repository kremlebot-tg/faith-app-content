#!/usr/bin/env python3
"""Сквозной редакторский аудит опубликованных тестов всех книг."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any

if __package__:
    from tools.audit_book_tests import audit_question
else:
    from audit_book_tests import audit_question


ROOT = Path(__file__).resolve().parents[1]
WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: ожидается JSON-объект")
    return value


def normalized(text: str) -> str:
    return " ".join(WORD_RE.findall(text.casefold()))


def source_paths(root: Path, book_id: str) -> list[Path]:
    combined = root / "content_tests" / f"{book_id}.json"
    if combined.is_file():
        return [combined]
    return sorted(
        (root / "content_tests" / "drafts").glob(f"{book_id}_*.json")
    )


def audit_published_corpus(
    root: Path,
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest = load_json(root / "manifest.json")
    book_ids = [
        str(book["id"])
        for book in manifest.get("library", [])
    ]

    seen_prompts: dict[str, str] = {}
    seen_explanations: dict[str, str] = {}
    seen_answer_sets: dict[tuple[str, ...], str] = {}
    prompt_stems: Counter[str] = Counter()
    explanation_stems: Counter[str] = Counter()
    correct_positions: Counter[int] = Counter()
    question_count = 0

    for book_id in book_ids:
        paths = source_paths(root, book_id)
        if not paths:
            errors.append(f"{book_id}: опубликованный корпус тестов не найден")
            continue
        seen_chapters: dict[int, str] = {}
        for path in paths:
            source = load_json(path)
            if source.get("book_id") != book_id:
                errors.append(f"{path.name}: неверный book_id")
                continue
            for chapter in source.get("chapters", []):
                number = chapter.get("number")
                location = f"{book_id}:глава {number}"
                if not isinstance(number, int):
                    errors.append(f"{path.name}: неверный номер главы {number!r}")
                    continue
                previous_chapter = seen_chapters.get(number)
                if previous_chapter is not None:
                    errors.append(
                        f"{location}: глава повторяет {previous_chapter}"
                    )
                else:
                    seen_chapters[number] = path.name

                for index, question in enumerate(chapter.get("test", []), start=1):
                    question_count += 1
                    question_location = f"{location}:вопрос {index}"
                    correct_index = audit_question(
                        question,
                        question_location,
                        errors,
                        warnings,
                    )
                    if correct_index is not None:
                        correct_positions[correct_index] += 1

                    prompt = normalized(str(question.get("question", "")))
                    explanation = normalized(
                        str(question.get("explanation", ""))
                    )
                    answers = tuple(
                        sorted(
                            normalized(str(answer.get("text", "")))
                            for answer in question.get("answers", [])
                            if isinstance(answer, dict)
                        )
                    )
                    for value, seen, label in (
                        (prompt, seen_prompts, "вопрос"),
                        (explanation, seen_explanations, "объяснение"),
                    ):
                        if not value:
                            continue
                        previous = seen.get(value)
                        if previous is not None:
                            errors.append(
                                f"{question_location}: {label} повторяет {previous}"
                            )
                        else:
                            seen[value] = question_location
                    if answers:
                        previous_answers = seen_answer_sets.get(answers)
                        if previous_answers is not None:
                            errors.append(
                                f"{question_location}: весь набор ответов повторяет "
                                f"{previous_answers}"
                            )
                        else:
                            seen_answer_sets[answers] = question_location

                    prompt_words = prompt.split()
                    explanation_words = explanation.split()
                    if len(prompt_words) >= 4:
                        prompt_stems[" ".join(prompt_words[:4])] += 1
                    if len(explanation_words) >= 5:
                        explanation_stems[
                            " ".join(explanation_words[:5])
                        ] += 1

    position_counts = [correct_positions[index] for index in range(3)]
    if position_counts and max(position_counts) - min(position_counts) > 1:
        errors.append(
            "в полном корпусе несбалансированы позиции верных ответов "
            f"{position_counts}"
        )

    for stem, count in prompt_stems.most_common():
        if count < 6:
            break
        warnings.append(
            f"начало вопроса «{stem}» повторяется в корпусе {count} раз"
        )
    for stem, count in explanation_stems.most_common():
        if count < 4:
            break
        warnings.append(
            f"начало объяснения «{stem}» повторяется в корпусе {count} раз"
        )

    stats = {
        "books": len(book_ids),
        "questions": question_count,
        "correct_positions": position_counts,
        "prompt_duplicates": 0
        if not errors
        else sum("вопрос повторяет" in error for error in errors),
        "explanation_duplicates": 0
        if not errors
        else sum("объяснение повторяет" in error for error in errors),
        "answer_set_duplicates": 0
        if not errors
        else sum("набор ответов повторяет" in error for error in errors),
    }
    return errors, warnings, stats


def main() -> int:
    errors, warnings, stats = audit_published_corpus(ROOT)
    print(
        f"books={stats['books']} questions={stats['questions']} "
        f"correct_positions={stats['correct_positions']} "
        f"prompt_duplicates={stats['prompt_duplicates']} "
        f"explanation_duplicates={stats['explanation_duplicates']} "
        f"answer_set_duplicates={stats['answer_set_duplicates']} "
        f"errors={len(errors)} warnings={len(warnings)}"
    )
    for message in errors:
        print(f"ERROR {message}")
    for message in warnings:
        print(f"WARN  {message}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
