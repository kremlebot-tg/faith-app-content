#!/usr/bin/env python3
"""Сквозной аудит полного корпуса книжных тестов в нескольких черновиках."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any

if __package__:
    from tools.audit_book_tests import audit_question, question_type
else:
    from audit_book_tests import audit_question, question_type


ROOT = Path(__file__).resolve().parents[1]
WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")


@dataclass(frozen=True)
class DraftCorpus:
    book_id: str
    chapter_count: int
    question_count: int


CORPORA = (
    DraftCorpus("ioann_damaskin", 100, 300),
    DraftCorpus("ignatij_prinoshenie", 60, 180),
    DraftCorpus("kirill_ierusalimskij_oglasitelnye", 24, 72),
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: ожидается JSON-объект")
    return value


def normalized(text: str) -> str:
    return " ".join(WORD_RE.findall(text.casefold()))


def audit_corpus(
    root: Path,
    corpus: DraftCorpus,
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    drafts_dir = root / "content_tests" / "drafts"
    paths = sorted(drafts_dir.glob(f"{corpus.book_id}_*.json"))
    if not paths:
        return (
            [f"{corpus.book_id}: черновики не найдены"],
            warnings,
            {
                "chapters": 0,
                "questions": 0,
                "keyed_positions": [0, 0, 0],
                "fourth_keyed_answers": 0,
                "question_types": {
                    "choice": 0,
                    "matching": 0,
                    "ordering": 0,
                    "cloze": 0,
                },
                "files": 0,
            },
        )

    book_path = root / f"{corpus.book_id}.json"
    if not book_path.is_file():
        return (
            [f"{corpus.book_id}: книга не найдена"],
            warnings,
            {
                "chapters": 0,
                "questions": 0,
                "keyed_positions": [0, 0, 0],
                "fourth_keyed_answers": 0,
                "question_types": {
                    "choice": 0,
                    "matching": 0,
                    "ordering": 0,
                    "cloze": 0,
                },
                "files": len(paths),
            },
        )
    book = load_json(book_path)
    expected_chapters = {
        int(chapter["number"])
        for chapter in book.get("chapters", [])
    }

    seen_chapters: dict[int, str] = {}
    seen_prompts: dict[str, str] = {}
    seen_explanations: dict[str, str] = {}
    seen_answer_sets: dict[tuple[str, ...], str] = {}
    prompt_stems: Counter[str] = Counter()
    explanation_stems: Counter[str] = Counter()
    keyed_positions: Counter[int] = Counter()
    type_counts: Counter[str] = Counter()
    question_count = 0

    for path in paths:
        source = load_json(path)
        if source.get("book_id") != corpus.book_id:
            errors.append(f"{path.name}: неверный book_id")
            continue
        for chapter in source.get("chapters", []):
            number = chapter.get("number")
            location = f"{path.name}:глава {number}"
            if not isinstance(number, int):
                errors.append(f"{path.name}: неверный номер главы {number!r}")
                continue
            previous_chapter = seen_chapters.get(number)
            if previous_chapter is not None:
                errors.append(
                    f"{location}: глава повторяет {previous_chapter}"
                )
            else:
                seen_chapters[number] = location
            raw_tests = chapter.get("test", [])
            tests = raw_tests if isinstance(raw_tests, list) else []
            if not isinstance(raw_tests, list):
                errors.append(f"{location}: test должен быть массивом")
            if len(tests) != 3:
                errors.append(f"{location}: требуется ровно 3 вопроса")
            for index, question in enumerate(tests, start=1):
                question_count += 1
                question_location = f"{location}:вопрос {index}"
                kind = question_type(question)
                if kind is not None:
                    type_counts[kind] += 1
                correct_index = audit_question(
                    question,
                    question_location,
                    errors,
                    warnings,
                )
                if correct_index is not None and kind in {"choice", "cloze"}:
                    keyed_positions[correct_index] += 1

                question_object = question if isinstance(question, dict) else {}
                prompt = normalized(str(question_object.get("question", "")))
                explanation = normalized(
                    str(question_object.get("explanation", ""))
                )
                raw_answers = question_object.get("answers", [])
                answer_items = raw_answers if isinstance(raw_answers, list) else []
                answers = tuple(
                    sorted(
                        normalized(str(answer.get("text", "")))
                        for answer in answer_items
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
                    explanation_stems[" ".join(explanation_words[:5])] += 1

    actual_chapters = set(seen_chapters)
    if actual_chapters != expected_chapters:
        errors.append(
            f"{corpus.book_id}: неполное покрытие глав, "
            f"пропущены={sorted(expected_chapters - actual_chapters)}, "
            f"лишние={sorted(actual_chapters - expected_chapters)}"
        )
    if len(actual_chapters) != corpus.chapter_count:
        errors.append(
            f"{corpus.book_id}: найдено {len(actual_chapters)} глав, "
            f"ожидалось {corpus.chapter_count}"
        )
    if question_count != corpus.question_count:
        errors.append(
            f"{corpus.book_id}: найдено {question_count} вопросов, "
            f"ожидалось {corpus.question_count}"
        )

    position_counts = [keyed_positions[index] for index in range(3)]
    if position_counts and max(position_counts) - min(position_counts) > 1:
        errors.append(
            f"{corpus.book_id}: несбалансированы позиции ключей choice/cloze "
            f"{position_counts}"
        )

    repeated_prompt_stems = [
        (stem, count)
        for stem, count in prompt_stems.most_common()
        if count >= 6
    ]
    repeated_explanation_stems = [
        (stem, count)
        for stem, count in explanation_stems.most_common()
        if count >= 4
    ]
    for stem, count in repeated_prompt_stems:
        warnings.append(
            f"{corpus.book_id}: начало вопроса «{stem}» повторяется {count} раз"
        )
    for stem, count in repeated_explanation_stems:
        warnings.append(
            f"{corpus.book_id}: начало объяснения «{stem}» повторяется {count} раз"
        )

    stats = {
        "chapters": len(actual_chapters),
        "questions": question_count,
        "keyed_positions": position_counts,
        "fourth_keyed_answers": keyed_positions[3],
        "question_types": {
            kind: type_counts[kind]
            for kind in ("choice", "matching", "ordering", "cloze")
        },
        "files": len(paths),
    }
    return errors, warnings, stats


def main() -> int:
    all_errors: list[str] = []
    all_warnings: list[str] = []
    for corpus in CORPORA:
        errors, warnings, stats = audit_corpus(ROOT, corpus)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        print(
            f"book={corpus.book_id} files={stats['files']} "
            f"chapters={stats['chapters']} questions={stats['questions']} "
            f"keyed_positions={stats['keyed_positions']} "
            f"fourth_keyed_answers={stats['fourth_keyed_answers']} "
            f"types={stats['question_types']} "
            f"errors={len(errors)} warnings={len(warnings)}"
        )
    for message in all_errors:
        print(f"ERROR {message}")
    for message in all_warnings:
        print(f"WARN  {message}")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
