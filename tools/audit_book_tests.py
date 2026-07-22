#!/usr/bin/env python3
"""Строгий аудит тестов к книгам перед публикацией release assets."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")
SECOND_PERSON_RE = re.compile(r"\b(?:ты|тебя|тебе|тобой|твой|твоя|твоё|твои)\b", re.I)
ANSWER_MARKERS = (
    (re.compile(r"\bистин\w*", re.I), "истин"),
    (re.compile(r"\bбожествен\w*", re.I), "божествен"),
    (re.compile(r"\bнастоящ\w*", re.I), "настоящ"),
    (re.compile(r"\bсам\b", re.I), "сам"),
)
DISTRACTOR_TELLS = (
    (re.compile(r"\bтолько\b", re.I), "только"),
    (re.compile(r"\bвсегда\b", re.I), "всегда"),
    (re.compile(r"\bникогда\b", re.I), "никогда"),
    (re.compile(r"\bнавсегда\b", re.I), "навсегда"),
    (re.compile(r"\bособого\b", re.I), "особого"),
    (re.compile(r"\bнемедлен\w*", re.I), "немедлен"),
)


def words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_question(
    question: dict[str, Any],
    location: str,
    errors: list[str],
    warnings: list[str],
) -> int | None:
    prompt = question.get("question", "").strip()
    explanation = question.get("explanation", "").strip()
    answers = question.get("answers", [])
    if question.get("type", "choice") != "choice":
        errors.append(f"{location}: книжный движок поддерживает только choice")
    if not prompt:
        errors.append(f"{location}: пустой вопрос")
    elif not prompt.endswith("?"):
        errors.append(f"{location}: формулировка вопроса должна оканчиваться знаком вопроса")
    if len(answers) != 3:
        errors.append(f"{location}: нужно ровно 3 варианта, найдено {len(answers)}")
    if not explanation:
        errors.append(f"{location}: отсутствует explanation")
    elif not 12 <= len(words(explanation)) <= 75:
        errors.append(
            f"{location}: explanation должен быть мини-уроком на 12–75 слов, "
            f"найдено {len(words(explanation))}"
        )
    if not answers:
        return None
    if any(not isinstance(answer, dict) for answer in answers):
        errors.append(f"{location}: вариант ответа не является объектом")
        return None
    if any(not answer.get("text", "").strip() for answer in answers):
        errors.append(f"{location}: пустой вариант ответа")
    answer_texts = [answer.get("text", "").strip() for answer in answers]
    normalized_answers = [text.rstrip(".?!").casefold() for text in answer_texts]
    if len(set(normalized_answers)) != len(normalized_answers):
        errors.append(f"{location}: варианты ответа не должны повторяться")
    if SECOND_PERSON_RE.search(" ".join([prompt, explanation, *answer_texts])):
        errors.append(f"{location}: прямое обращение на «ты»")
    if any(not isinstance(answer.get("correct"), bool) for answer in answers):
        errors.append(f"{location}: correct должен быть bool у каждого варианта")
        return None
    correct_indices = [i for i, answer in enumerate(answers) if answer["correct"]]
    if len(correct_indices) != 1:
        errors.append(
            f"{location}: должен быть ровно 1 correct:true, найдено {len(correct_indices)}"
        )
        return None
    lengths = [len(words(answer["text"])) for answer in answers]
    if max(lengths) - min(lengths) > 3:
        errors.append(f"{location}: несбалансированные варианты по словам {lengths}")
    correct_index = correct_indices[0]
    if lengths[correct_index] == max(lengths) and lengths.count(max(lengths)) == 1:
        errors.append(f"{location}: верный ответ единственный самый длинный {lengths}")
    for pattern, label in ANSWER_MARKERS:
        if pattern.search(answer_texts[correct_index]) and not any(
            pattern.search(text)
            for i, text in enumerate(answer_texts)
            if i != correct_index
        ):
            errors.append(
                f"{location}: слово-маркер «{label}» встречается только в верном ответе"
            )
    for pattern, label in DISTRACTOR_TELLS:
        if not pattern.search(answer_texts[correct_index]) and any(
            pattern.search(text)
            for i, text in enumerate(answer_texts)
            if i != correct_index
        ):
            errors.append(
                f"{location}: формальная подсказка «{label}» встречается только в дистракторе"
            )
    if prompt.rstrip(".?!").lower() == answers[correct_index]["text"].rstrip(".?!").lower():
        warnings.append(f"{location}: вопрос повторяет верный ответ")
    return correct_index


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    books = 0
    chapters = 0
    questions = 0

    for source_path in sorted((ROOT / "content_tests").glob("*.json")):
        source = load(source_path)
        book_path = ROOT / f'{source["book_id"]}.json'
        if not book_path.exists():
            errors.append(f"{source_path.name}: нет соответствующего файла книги")
            continue
        book = load(book_path)
        books += 1
        embedded = {
            chapter["number"]: chapter.get("test", [])
            for chapter in book["chapters"]
        }
        book_numbers = set(embedded)
        seen_numbers: set[int] = set()
        excluded_numbers: set[int] = set()
        seen_prompts: dict[str, str] = {}
        correct_positions: list[int] = []
        for item in source.get("excluded_chapters", []):
            if not isinstance(item, dict):
                errors.append(
                    f"{source_path.name}: исключённая глава требует number и reason"
                )
                continue
            number = item.get("number")
            reason = item.get("reason")
            if (
                not isinstance(number, int)
                or not isinstance(reason, str)
                or not reason.strip()
            ):
                errors.append(
                    f"{source_path.name}: исключённая глава требует number и reason"
                )
                continue
            if number in excluded_numbers:
                errors.append(
                    f"{source_path.name}: исключённая глава {number} повторяется"
                )
            excluded_numbers.add(number)
            if embedded.get(number):
                errors.append(
                    f"{source_path.name}: исключённая глава {number} содержит встроенный тест"
                )
        for chapter in source.get("chapters", []):
            number = chapter["number"]
            if number in seen_numbers:
                errors.append(f"{source_path.name}: глава {number} повторяется")
            seen_numbers.add(number)
            tests = chapter.get("test", [])
            chapters += 1
            if len(tests) != 3:
                errors.append(
                    f"{source_path.name}: глава {number} должна содержать ровно 3 вопроса"
                )
            if embedded.get(number) != tests:
                errors.append(
                    f"{source_path.name}: тесты главы {number} не встроены в актуальный JSON книги"
                )
            for index, question in enumerate(tests, 1):
                questions += 1
                location = f"{source_path.name}:глава {number}:вопрос {index}"
                normalized_prompt = question.get("question", "").strip().casefold()
                if normalized_prompt:
                    previous = seen_prompts.get(normalized_prompt)
                    if previous is not None:
                        errors.append(
                            f"{location}: вопрос повторяет формулировку из {previous}"
                        )
                    else:
                        seen_prompts[normalized_prompt] = location
                correct_position = audit_question(
                    question,
                    location,
                    errors,
                    warnings,
                )
                if correct_position is not None:
                    correct_positions.append(correct_position)
        overlap = seen_numbers & excluded_numbers
        if overlap:
            errors.append(
                f"{source_path.name}: главы одновременно проверяются и исключены {sorted(overlap)}"
            )
        accounted = seen_numbers | excluded_numbers
        if accounted != book_numbers:
            missing = sorted(book_numbers - accounted)
            extra = sorted(accounted - book_numbers)
            errors.append(
                f"{source_path.name}: неполное покрытие глав, "
                f"пропущены={missing}, лишние={extra}"
            )
        if correct_positions:
            distribution = Counter(correct_positions)
            counts = [distribution[index] for index in range(3)]
            if max(counts) - min(counts) > 1:
                errors.append(
                    f"{source_path.name}: несбалансированы позиции верных ответов {counts}"
                )

    print(
        f"books={books} tested_chapters={chapters} questions={questions} "
        f"errors={len(errors)} warnings={len(warnings)}"
    )
    for message in errors:
        print(f"ERROR {message}")
    for message in warnings:
        print(f"WARN  {message}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
