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
QUESTION_TYPES = frozenset({"choice", "matching", "ordering", "cloze"})
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


def normalized_text(text: str) -> str:
    return " ".join(text.split()).casefold()


def question_type(question: object) -> str | None:
    if not isinstance(question, dict):
        return None
    value = question.get("type", "choice")
    return value if isinstance(value, str) and value in QUESTION_TYPES else None


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_books(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "manifest.json"
    if not path.is_file():
        return {}
    manifest = load(path)
    return {
        str(book["id"]): book
        for book in manifest.get("library", [])
    }


def book_and_tests_paths(
    root: Path,
    book_id: str,
    manifest_entry: dict[str, Any] | None,
) -> tuple[Path, Path | None]:
    local_book = root / f"{book_id}.json"
    if local_book.is_file() or not manifest_entry or not manifest_entry.get("bundled"):
        return local_book, None

    bundle_path = Path(str(manifest_entry.get("bundle_path", "")))
    app_root = root.parent / "faith_app"
    book_path = app_root / bundle_path
    tests_path = book_path.with_name(f"{book_id}_tests.json")
    return book_path, tests_path


def _audit_forbidden_fields(
    question: dict[str, Any],
    fields: set[str],
    question_kind: str,
    location: str,
    errors: list[str],
) -> None:
    for field in sorted(fields):
        if field in question:
            errors.append(
                f"{location}: поле {field!r} недопустимо для типа {question_kind}"
            )


def _audit_answers(
    raw_answers: object,
    *,
    minimum: int,
    maximum: int,
    exact: int | None,
    require_unique: bool,
    location: str,
    errors: list[str],
) -> tuple[list[str], int | None]:
    if not isinstance(raw_answers, list):
        errors.append(f"{location}: answers должен быть массивом")
        return [], None

    if exact is not None and len(raw_answers) != exact:
        errors.append(
            f"{location}: нужно ровно {exact} варианта, найдено {len(raw_answers)}"
        )
    elif not minimum <= len(raw_answers) <= maximum:
        errors.append(
            f"{location}: нужно от {minimum} до {maximum} вариантов, "
            f"найдено {len(raw_answers)}"
        )

    answer_texts: list[str] = []
    correct_indices: list[int] = []
    structurally_valid = True
    for index, raw_answer in enumerate(raw_answers):
        answer_location = f"{location}:answers[{index}]"
        if not isinstance(raw_answer, dict):
            errors.append(f"{answer_location}: вариант ответа не является объектом")
            answer_texts.append("")
            structurally_valid = False
            continue
        text = raw_answer.get("text")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{answer_location}: пустой вариант ответа")
            answer_texts.append("")
            structurally_valid = False
        else:
            answer_texts.append(text.strip())
        correct = raw_answer.get("correct")
        if not isinstance(correct, bool):
            errors.append(f"{answer_location}: correct должен быть bool")
            structurally_valid = False
        elif correct:
            correct_indices.append(index)

    if require_unique:
        normalized_answers = [
            normalized_text(text.rstrip(".?!")) for text in answer_texts
        ]
        if (
            all(normalized_answers)
            and len(set(normalized_answers)) != len(normalized_answers)
        ):
            errors.append(f"{location}: варианты ответа не должны повторяться")

    if len(correct_indices) != 1:
        errors.append(
            f"{location}: должен быть ровно 1 correct:true, "
            f"найдено {len(correct_indices)}"
        )
        return answer_texts, None
    if not structurally_valid:
        return answer_texts, None
    return answer_texts, correct_indices[0]


def _audit_choice(
    question: dict[str, Any],
    *,
    prompt: str,
    location: str,
    errors: list[str],
    warnings: list[str],
) -> int | None:
    _audit_forbidden_fields(
        question,
        {"pairs", "items", "prompt"},
        "choice",
        location,
        errors,
    )
    if prompt and not prompt.endswith("?"):
        errors.append(
            f"{location}: формулировка вопроса должна оканчиваться знаком вопроса"
        )
    answer_texts, correct_index = _audit_answers(
        question.get("answers"),
        minimum=3,
        maximum=3,
        exact=3,
        require_unique=True,
        location=location,
        errors=errors,
    )
    if correct_index is None or len(answer_texts) != 3 or not all(answer_texts):
        return None

    _audit_answer_quality(
        answer_texts,
        correct_index=correct_index,
        location=location,
        errors=errors,
        warnings=warnings,
        question_prompt=prompt,
    )
    return correct_index


def _audit_answer_quality(
    answer_texts: list[str],
    *,
    correct_index: int,
    location: str,
    errors: list[str],
    warnings: list[str],
    question_prompt: str | None = None,
) -> None:
    lengths = [len(words(text)) for text in answer_texts]
    if max(lengths) - min(lengths) > 3:
        errors.append(f"{location}: несбалансированные варианты по словам {lengths}")
    if lengths[correct_index] == max(lengths) and lengths.count(max(lengths)) == 1:
        errors.append(f"{location}: верный ответ единственный самый длинный {lengths}")
    for pattern, label in ANSWER_MARKERS:
        if pattern.search(answer_texts[correct_index]) and not any(
            pattern.search(text)
            for index, text in enumerate(answer_texts)
            if index != correct_index
        ):
            errors.append(
                f"{location}: слово-маркер «{label}» встречается только в верном ответе"
            )
    for pattern, label in DISTRACTOR_TELLS:
        if not pattern.search(answer_texts[correct_index]) and any(
            pattern.search(text)
            for index, text in enumerate(answer_texts)
            if index != correct_index
        ):
            errors.append(
                f"{location}: формальная подсказка «{label}» встречается "
                "только в дистракторе"
            )
    if (
        question_prompt is not None
        and normalized_text(question_prompt.rstrip(".?!"))
        == normalized_text(answer_texts[correct_index].rstrip(".?!"))
    ):
        warnings.append(f"{location}: вопрос повторяет верный ответ")


def _audit_matching(
    question: dict[str, Any],
    *,
    location: str,
    errors: list[str],
) -> None:
    _audit_forbidden_fields(
        question,
        {"answers", "items", "prompt"},
        "matching",
        location,
        errors,
    )
    pairs = question.get("pairs")
    if not isinstance(pairs, list):
        errors.append(f"{location}: pairs должен быть массивом")
        return
    if len(pairs) != 3:
        errors.append(
            f"{location}: matching требует ровно 3 пары, найдено {len(pairs)}"
        )

    left_values: list[str] = []
    right_values: list[str] = []
    for index, pair in enumerate(pairs):
        pair_location = f"{location}:pairs[{index}]"
        if not isinstance(pair, dict):
            errors.append(f"{pair_location}: пара не является объектом")
            continue
        for field, values in (("left", left_values), ("right", right_values)):
            value = pair.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{pair_location}: поле {field} должно быть непустым")
                continue
            values.append(value.strip())
    for field, values in (("left", left_values), ("right", right_values)):
        normalized = [normalized_text(value) for value in values]
        if len(set(normalized)) != len(normalized):
            errors.append(
                f"{location}: значения {field} в matching должны быть уникальны"
            )


def _audit_ordering(
    question: dict[str, Any],
    *,
    location: str,
    errors: list[str],
) -> None:
    _audit_forbidden_fields(
        question,
        {"answers", "pairs", "prompt"},
        "ordering",
        location,
        errors,
    )
    items = question.get("items")
    if not isinstance(items, list):
        errors.append(f"{location}: items должен быть массивом")
        return
    if not 3 <= len(items) <= 5:
        errors.append(
            f"{location}: ordering требует от 3 до 5 элементов, найдено {len(items)}"
        )
    values: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{location}:items[{index}]: элемент должен быть непустым")
        else:
            values.append(item.strip())
    normalized = [normalized_text(value) for value in values]
    if len(set(normalized)) != len(normalized):
        errors.append(f"{location}: элементы ordering должны быть уникальны")


def _audit_cloze(
    question: dict[str, Any],
    *,
    location: str,
    errors: list[str],
    warnings: list[str],
) -> int | None:
    _audit_forbidden_fields(
        question,
        {"pairs", "items"},
        "cloze",
        location,
        errors,
    )
    prompt = question.get("prompt")
    if (
        not isinstance(prompt, str)
        or not prompt.strip()
        or prompt.count("___") != 1
        or prompt.count("_") != 3
    ):
        errors.append(f"{location}: cloze prompt должен содержать ровно один ___")
    answer_texts, correct_index = _audit_answers(
        question.get("answers"),
        minimum=2,
        maximum=4,
        exact=None,
        require_unique=True,
        location=location,
        errors=errors,
    )
    if correct_index is not None and answer_texts and all(answer_texts):
        _audit_answer_quality(
            answer_texts,
            correct_index=correct_index,
            location=location,
            errors=errors,
            warnings=warnings,
        )
    return correct_index


def audit_question(
    question: object,
    location: str,
    errors: list[str],
    warnings: list[str],
) -> int | None:
    if not isinstance(question, dict):
        errors.append(f"{location}: вопрос не является объектом")
        return None

    raw_type = question.get("type", "choice")
    if not isinstance(raw_type, str) or raw_type not in QUESTION_TYPES:
        errors.append(f"{location}: неизвестный тип задания {raw_type!r}")
        return None
    kind = raw_type

    raw_prompt = question.get("question")
    prompt = raw_prompt.strip() if isinstance(raw_prompt, str) else ""
    if not prompt:
        errors.append(f"{location}: пустой вопрос")

    raw_explanation = question.get("explanation")
    explanation = (
        raw_explanation.strip() if isinstance(raw_explanation, str) else ""
    )
    if not explanation:
        errors.append(f"{location}: отсутствует explanation")
    elif not 12 <= len(words(explanation)) <= 75:
        errors.append(
            f"{location}: explanation должен быть мини-уроком на 12–75 слов, "
            f"найдено {len(words(explanation))}"
        )

    direct_address_texts = [prompt, explanation]
    context = question.get("context")
    if context is not None:
        if not isinstance(context, str) or not context.strip():
            errors.append(f"{location}: context должен быть непустой строкой")
        else:
            direct_address_texts.append(context)
    for field in ("prompt",):
        value = question.get(field)
        if isinstance(value, str):
            direct_address_texts.append(value)
    for field in ("answers", "pairs", "items"):
        value = question.get(field)
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, str):
                direct_address_texts.append(item)
            elif isinstance(item, dict):
                direct_address_texts.extend(
                    child
                    for key in ("text", "left", "right")
                    if isinstance((child := item.get(key)), str)
                )
    if SECOND_PERSON_RE.search(" ".join(direct_address_texts)):
        errors.append(f"{location}: прямое обращение на «ты»")

    if kind == "choice":
        return _audit_choice(
            question,
            prompt=prompt,
            location=location,
            errors=errors,
            warnings=warnings,
        )
    if kind == "matching":
        _audit_matching(question, location=location, errors=errors)
        return None
    if kind == "ordering":
        _audit_ordering(question, location=location, errors=errors)
        return None
    return _audit_cloze(
        question,
        location=location,
        errors=errors,
        warnings=warnings,
    )


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    books = 0
    chapters = 0
    questions = 0
    type_counts: Counter[str] = Counter()
    books_by_id = manifest_books(ROOT)

    for source_path in sorted((ROOT / "content_tests").glob("*.json")):
        source = load(source_path)
        book_id = str(source["book_id"])
        manifest_entry = books_by_id.get(book_id)
        book_path, separate_tests_path = book_and_tests_paths(
            ROOT,
            book_id,
            manifest_entry,
        )
        if not book_path.exists():
            if not manifest_entry or not manifest_entry.get("bundled"):
                errors.append(f"{source_path.name}: нет соответствующего файла книги")
                continue
            chapter_count = manifest_entry.get("chapters_count")
            if not isinstance(chapter_count, int) or chapter_count < 1:
                errors.append(
                    f"{source_path.name}: для встроенной книги нужен chapters_count"
                )
                continue
            book = None
            book_numbers = set(range(1, chapter_count + 1))
            embedded = {
                chapter["number"]: chapter.get("test", [])
                for chapter in source.get("chapters", [])
            }
        else:
            book = load(book_path)
            book_numbers = {
                chapter["number"]
                for chapter in book.get("chapters", [])
            }
            if separate_tests_path is not None:
                if not separate_tests_path.is_file():
                    errors.append(
                        f"{source_path.name}: нет встроенного файла тестов приложения"
                    )
                    continue
                published_source = load(separate_tests_path)
                if published_source.get("book_id") != book_id:
                    errors.append(
                        f"{separate_tests_path.name}: неверный book_id"
                    )
                embedded = {
                    chapter["number"]: chapter.get("test", [])
                    for chapter in published_source.get("chapters", [])
                }
            else:
                embedded = {
                    chapter["number"]: chapter.get("test", [])
                    for chapter in book["chapters"]
                }
        books += 1
        seen_numbers: set[int] = set()
        excluded_numbers: set[int] = set()
        seen_prompts: dict[str, str] = {}
        keyed_positions: Counter[int] = Counter()
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
                    f"{source_path.name}: исключённая глава {number} "
                    "содержит встроенный тест"
                )
        for chapter in source.get("chapters", []):
            number = chapter["number"]
            if number in seen_numbers:
                errors.append(f"{source_path.name}: глава {number} повторяется")
            seen_numbers.add(number)
            raw_tests = chapter.get("test", [])
            tests = raw_tests if isinstance(raw_tests, list) else []
            chapters += 1
            if not isinstance(raw_tests, list):
                errors.append(
                    f"{source_path.name}: глава {number}: test должен быть массивом"
                )
            if len(tests) != 3:
                errors.append(
                    f"{source_path.name}: глава {number} должна содержать "
                    "ровно 3 вопроса"
                )
            if embedded.get(number) != tests:
                errors.append(
                    f"{source_path.name}: тесты главы {number} не встроены "
                    "в актуальный JSON книги"
                )
            for index, question in enumerate(tests, 1):
                questions += 1
                location = f"{source_path.name}:глава {number}:вопрос {index}"
                kind = question_type(question)
                if kind is not None:
                    type_counts[kind] += 1
                raw_prompt = (
                    question.get("question")
                    if isinstance(question, dict)
                    else None
                )
                normalized_prompt = (
                    raw_prompt.strip().casefold()
                    if isinstance(raw_prompt, str)
                    else ""
                )
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
                if (
                    correct_position is not None
                    and kind in {"choice", "cloze"}
                ):
                    keyed_positions[correct_position] += 1
        overlap = seen_numbers & excluded_numbers
        if overlap:
            errors.append(
                f"{source_path.name}: главы одновременно проверяются "
                f"и исключены {sorted(overlap)}"
            )
        accounted = seen_numbers | excluded_numbers
        if accounted != book_numbers:
            missing = sorted(book_numbers - accounted)
            extra = sorted(accounted - book_numbers)
            errors.append(
                f"{source_path.name}: неполное покрытие глав, "
                f"пропущены={missing}, лишние={extra}"
            )
        if keyed_positions:
            counts = [keyed_positions[index] for index in range(3)]
            if max(counts) - min(counts) > 1:
                errors.append(
                    f"{source_path.name}: несбалансированы позиции ключей {counts}"
                )

    print(
        f"books={books} tested_chapters={chapters} questions={questions} "
        f"choice={type_counts['choice']} matching={type_counts['matching']} "
        f"ordering={type_counts['ordering']} cloze={type_counts['cloze']} "
        f"errors={len(errors)} warnings={len(warnings)}"
    )
    for message in errors:
        print(f"ERROR {message}")
    for message in warnings:
        print(f"WARN  {message}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
