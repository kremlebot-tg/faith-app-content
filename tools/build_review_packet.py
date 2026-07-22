#!/usr/bin/env python3
"""Build a deterministic Markdown packet for human theological review.

The generator deliberately copies questions, answers, and explanations without
editing them.  It adds only review metadata, compact source excerpts, and empty
verdict fields.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


CONTENT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APP_ROOT = CONTENT_ROOT.parent / "faith_app"
DEFAULT_OUTPUT_DIR = CONTENT_ROOT / "reviews" / "v1.3.1"
EXCERPT_LIMIT = 700


@dataclass(frozen=True)
class ReviewBook:
    slug: str
    filename: str
    prefix: str
    data: dict[str, Any]
    tests_by_chapter: dict[int, list[dict[str, Any]]]
    source_path: Path
    test_path: Path | None
    repository: str
    commit: str
    excluded_chapters: tuple[int, ...]
    risk_tags: dict[int, tuple[str, ...]]

    @property
    def tested_chapters(self) -> list[dict[str, Any]]:
        return [
            chapter
            for chapter in self.data["chapters"]
            if int(chapter["number"]) in self.tests_by_chapter
        ]

    @property
    def question_count(self) -> int:
        return sum(len(test) for test in self.tests_by_chapter.values())


LADDER_RISKS = {
    4: ("послушание и пределы власти",),
    5: ("уныние, отчаяние и риск самоповреждения",),
    6: ("уныние, отчаяние и риск самоповреждения",),
    10: ("насилие, защита и обращение за помощью",),
    12: ("ложь и нравственные исключения",),
    14: ("пост, тело и целомудрие",),
    15: ("пост, тело и целомудрие",),
    18: ("уныние, отчаяние и риск самоповреждения",),
    19: ("пост, тело и целомудрие",),
    20: ("пост, тело и целомудрие",),
    21: ("уныние, отчаяние и риск самоповреждения",),
    23: ("уныние, отчаяние и риск самоповреждения",),
    26: ("послушание и пределы власти",),
    27: ("безмолвие, Промысл и бесстрастие",),
    28: ("безмолвие, Промысл и бесстрастие",),
    29: ("безмолвие, Промысл и бесстрастие",),
    30: ("безмолвие, Промысл и бесстрастие",),
}

FEOFAN_RISKS = {
    **{
        number: ("Таинства, благодать и свобода",)
        for number in (*range(1, 15), 20, 24, 25, 26)
    },
    17: ("безмолвие, Промысл и бесстрастие",),
    18: ("безмолвие, Промысл и бесстрастие",),
    19: ("безмолвие, Промысл и бесстрастие",),
    22: ("пост, тело и целомудрие",),
    27: ("безмолвие, Промысл и бесстрастие",),
    28: ("безмолвие, Промысл и бесстрастие",),
    29: ("безмолвие, Промысл и бесстрастие",),
    30: ("атрибуция и границы авторского текста",),
}

AVVA_RISKS = {
    1: ("послушание и пределы власти",),
    4: ("насилие, защита и обращение за помощью",),
    5: ("послушание и пределы власти",),
    7: (
        "уныние, отчаяние и риск самоповреждения",
        "насилие, защита и обращение за помощью",
    ),
    8: (
        "уныние, отчаяние и риск самоповреждения",
        "насилие, защита и обращение за помощью",
    ),
    9: ("ложь и нравственные исключения",),
    13: ("уныние, отчаяние и риск самоповреждения",),
    15: ("пост, тело и целомудрие",),
    17: (
        "послушание и пределы власти",
        "насилие, защита и обращение за помощью",
    ),
    18: (
        "послушание и пределы власти",
        "насилие, защита и обращение за помощью",
    ),
    20: ("атрибуция и границы авторского текста",),
    21: ("атрибуция и границы авторского текста",),
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _short(commit: str) -> str:
    return commit[:7]


def _chapter_map(chapters: Iterable[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for chapter in chapters:
        number = int(chapter["number"])
        if number in result:
            raise ValueError(f"duplicate chapter number: {number}")
        result[number] = chapter
    return result


def _embedded_tests(data: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    return {
        int(chapter["number"]): chapter["test"]
        for chapter in data["chapters"]
        if chapter.get("test")
    }


def _external_tests(data: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    return {
        int(chapter["number"]): chapter["test"]
        for chapter in data["chapters"]
        if chapter.get("test")
    }


def _validate_book(book: ReviewBook) -> None:
    chapters = _chapter_map(book.data.get("chapters", []))
    declared_count = int(book.data.get("chapters_count", len(chapters)))
    if declared_count != len(chapters):
        raise ValueError(
            f"{book.slug}: chapters_count={declared_count}, actual={len(chapters)}"
        )

    expected_tested = set(chapters) - set(book.excluded_chapters)
    actual_tested = set(book.tests_by_chapter)
    if actual_tested != expected_tested:
        missing = sorted(expected_tested - actual_tested)
        extra = sorted(actual_tested - expected_tested)
        raise ValueError(
            f"{book.slug}: unexpected test coverage; missing={missing}, extra={extra}"
        )

    for number in sorted(actual_tested):
        questions = book.tests_by_chapter[number]
        if len(questions) != 3:
            raise ValueError(
                f"{book.slug} chapter {number}: expected 3 questions, got {len(questions)}"
            )
        for index, question in enumerate(questions, start=1):
            if not str(question.get("question", "")).strip():
                raise ValueError(
                    f"{book.slug} chapter {number}, question {index}: empty question"
                )
            answers = question.get("answers")
            if not isinstance(answers, list) or len(answers) < 2:
                raise ValueError(
                    f"{book.slug} chapter {number}, question {index}: invalid answers"
                )
            if sum(answer.get("correct") is True for answer in answers) != 1:
                raise ValueError(
                    f"{book.slug} chapter {number}, question {index}: "
                    "expected exactly one correct answer"
                )
            if any(not str(answer.get("text", "")).strip() for answer in answers):
                raise ValueError(
                    f"{book.slug} chapter {number}, question {index}: empty answer"
                )
            if not str(question.get("explanation", "")).strip():
                raise ValueError(
                    f"{book.slug} chapter {number}, question {index}: empty explanation"
                )


def load_books(
    content_root: Path,
    app_root: Path,
    content_commit: str,
    app_commit: str,
) -> list[ReviewBook]:
    ladder_path = content_root / "ioann_lestvichnik.json"
    feofan_path = content_root / "feofan_put_ko_spaseniyu.json"
    avva_path = app_root / "assets/library/avva_dorofey.json"
    avva_tests_path = app_root / "assets/library/avva_dorofey_tests.json"

    ladder = _load_json(ladder_path)
    feofan = _load_json(feofan_path)
    avva = _load_json(avva_path)
    avva_tests = _load_json(avva_tests_path)

    if ladder.get("id") != "ioann_lestvichnik" or ladder.get("version") != 3:
        raise ValueError("ioann_lestvichnik.json must be the cleaned version 3")
    if feofan.get("id") != "feofan_put_ko_spaseniyu":
        raise ValueError("unexpected Feofan book id")
    if avva.get("id") != "avva_dorofey":
        raise ValueError("unexpected Avva Dorotheus book id")
    if avva_tests.get("book_id") != "avva_dorofey":
        raise ValueError("Avva Dorotheus tests target another book")

    books = [
        ReviewBook(
            slug="lestvitsa",
            filename="01_lestvitsa.md",
            prefix="Л",
            data=ladder,
            tests_by_chapter=_embedded_tests(ladder),
            source_path=ladder_path,
            test_path=None,
            repository="faith-app-content",
            commit=content_commit,
            excluded_chapters=(),
            risk_tags=LADDER_RISKS,
        ),
        ReviewBook(
            slug="feofan",
            filename="02_feofan.md",
            prefix="Ф",
            data=feofan,
            tests_by_chapter=_embedded_tests(feofan),
            source_path=feofan_path,
            test_path=None,
            repository="faith-app-content",
            commit=content_commit,
            excluded_chapters=(9, 12, 31, 32, 33),
            risk_tags=FEOFAN_RISKS,
        ),
        ReviewBook(
            slug="avva_dorofey",
            filename="03_avva_dorofey.md",
            prefix="Д",
            data=avva,
            tests_by_chapter=_external_tests(avva_tests),
            source_path=avva_path,
            test_path=avva_tests_path,
            repository="faith_app",
            commit=app_commit,
            excluded_chapters=(22,),
            risk_tags=AVVA_RISKS,
        ),
    ]
    for book in books:
        _validate_book(book)
    return books


def source_excerpt(chapter: dict[str, Any], limit: int = EXCERPT_LIMIT) -> str:
    """Return an exact leading excerpt, truncating only at a word boundary."""

    paragraph = next(
        (str(value).strip() for value in chapter.get("paragraphs", []) if str(value).strip()),
        "",
    )
    if not paragraph:
        raise ValueError(f"chapter {chapter.get('number')} has no source paragraph")
    if len(paragraph) <= limit:
        return paragraph
    prefix = paragraph[: limit + 1]
    boundary = prefix.rfind(" ")
    if boundary <= 0:
        boundary = limit
    return paragraph[:boundary].rstrip() + "…"


def _answer_label(index: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if index >= len(alphabet):
        raise ValueError("too many answers for Markdown review format")
    return alphabet[index]


def _render_book(book: ReviewBook) -> str:
    data = book.data
    source_sha = _sha256(book.source_path)
    lines = [
        f"# {data['work']}",
        "",
        f"- Автор: {data['author']}",
        f"- Версия книги: {data['version']}",
        f"- Репозиторий: `{book.repository}`",
        f"- Базовый commit входных данных: `{book.commit}`",
        f"- SHA-256 текста книги: `{source_sha}`",
        f"- Источник: [{data['source']}]({data['source']})",
        f"- Лицензия в метаданных: `{data['license']}`",
        f"- Глав с тестами: {len(book.tested_chapters)}",
        f"- Вопросов: {book.question_count}",
    ]
    if book.test_path is not None:
        lines.append(f"- SHA-256 файла тестов: `{_sha256(book.test_path)}`")
    if book.excluded_chapters:
        excluded = ", ".join(str(number) for number in book.excluded_chapters)
        lines.append(f"- Не входят в рецензию тестов: главы {excluded}")
    lines.extend(
        [
            "",
            "Текст вопросов, ответов и объяснений перенесён без богословской "
            "редактуры. Фрагмент источника приведён только для быстрой ориентации; "
            "при сомнении следует открыть полный текст по ссылке выше.",
            "",
        ]
    )

    for chapter in book.tested_chapters:
        number = int(chapter["number"])
        chapter_id = f"{book.prefix}{number:02d}"
        tags = book.risk_tags.get(number, ("общая богословская и аскетическая точность",))
        lines.extend(
            [
                f"## {chapter_id} · {chapter['title']}",
                "",
                "**Риск-теги:** " + "; ".join(f"`{tag}`" for tag in tags),
                "",
                "**Фрагмент источника (начало главы):**",
                "",
                f"> {source_excerpt(chapter)}",
                "",
            ]
        )
        for question_index, question in enumerate(
            book.tests_by_chapter[number], start=1
        ):
            question_id = f"{chapter_id}.{question_index}"
            correct_index = next(
                index
                for index, answer in enumerate(question["answers"])
                if answer["correct"] is True
            )
            lines.extend(
                [
                    f"### {question_id}",
                    "",
                    f"**Вопрос:** {question['question']}",
                    "",
                ]
            )
            for answer_index, answer in enumerate(question["answers"]):
                lines.append(
                    f"- {_answer_label(answer_index)}. {answer['text']}"
                )
            lines.extend(
                [
                    "",
                    f"**Ключ:** {_answer_label(correct_index)}",
                    "",
                    f"**Объяснение:** {question['explanation']}",
                    "",
                    "**Вердикт:** ☐ принять ☐ исправить ☐ снять вопрос",
                    "",
                    "**Замечание / предлагаемая правка:**",
                    "",
                    "---",
                    "",
                ]
            )
        lines.extend(
            [
                f"**Итог {chapter_id}:** ☐ проверено полностью; иных "
                "богословских замечаний нет ☐ требуется доработка",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_readme(
    books: list[ReviewBook], content_commit: str, app_commit: str
) -> str:
    by_slug = {book.slug: book for book in books}
    ladder = by_slug["lestvitsa"]
    feofan = by_slug["feofan"]
    avva = by_slug["avva_dorofey"]
    total_questions = sum(book.question_count for book in books)
    lines = [
        "<!-- build-review-packet: "
        f"content={content_commit} app={app_commit} -->",
        "# Пакет богословской рецензии тестов v1.3.1",
        "",
        "Пакет предназначен для человеческой проверки богословской точности, "
        "пастырской безопасности и ясности тестов к трём книгам. Он не заменяет "
        "чтение полного первоисточника и не содержит богословских правок исходного "
        "текста тестов.",
        "",
        "## Зафиксированные входные данные",
        "",
        f"- `faith-app-content`: `{content_commit}`",
        f"- `faith_app`: `{app_commit}`",
        f"- Всего: {len(ladder.tested_chapters) + len(feofan.tested_chapters) + len(avva.tested_chapters)} глав с тестами, {total_questions} вопросов.",
        "",
        "Commit ID фиксирует базу соответствующего репозитория. "
        "Точные входные файлы, включая очищенную «Лествицу» v3, "
        "дополнительно зафиксированы SHA-256 в начале каждого файла книги.",
        "",
        "| Файл | Книга | Версия | Главы с тестами | Вопросы |",
        "|---|---|---:|---:|---:|",
        f"| [01_lestvitsa.md](01_lestvitsa.md) | {ladder.data['work']} | {ladder.data['version']} | {len(ladder.tested_chapters)} | {ladder.question_count} |",
        f"| [02_feofan.md](02_feofan.md) | {feofan.data['work']} | {feofan.data['version']} | {len(feofan.tested_chapters)} | {feofan.question_count} |",
        f"| [03_avva_dorofey.md](03_avva_dorofey.md) | {avva.data['work']} | {avva.data['version']} | {len(avva.tested_chapters)} | {avva.question_count} |",
        "",
        "Исключения соответствуют структуре приложения: у Феофана нет тестов к "
        "главам 9, 12, 31, 32 и 33; у аввы Дорофея глава 22 содержит примечания; "
        "у «Лествицы» тестами покрыты все 30 слов.",
        "",
        "## Что проверять",
        "",
        "Для каждого вопроса необходимо проверить:",
        "",
        "1. соответствует ли ключ первоисточнику и православному вероучению;",
        "2. не искажает ли объяснение смысл автора и границы его наставления;",
        "3. не превращён ли монашеский совет в безусловное правило для мирянина;",
        "4. не оправдывает ли формулировка насилие, духовное давление, отказ от "
        "лечения или сокрытие опасности;",
        "5. остаются ли дистракторы неверными без карикатуры и двусмысленности.",
        "",
        "## Приоритетные зоны",
        "",
        "- Послушание и пределы власти: Л04, Л26; Д01, Д05, Д17–Д18.",
        "- Уныние, отчаяние и риск самоповреждения: Л05–Л06, Л18, Л21, Л23; Д07–Д08, Д13.",
        "- Насилие, защита и обращение за помощью: Л10; Д04, Д07–Д08, Д17–Д18.",
        "- Пост, тело и целомудрие: Л14–Л15, Л19–Л20; Ф22; Д15.",
        "- Таинства, благодать и свобода: Ф01–Ф14, Ф20, Ф24–Ф26.",
        "- Безмолвие, Промысл и бесстрастие: Л27–Л30; Ф17–Ф19, Ф27–Ф29.",
        "- Ложь и нравственные исключения: Л12; Д09.",
        "- Атрибуция и границы авторского текста: Ф30; Д20–Д21.",
        "",
        "Риск-тег указывает, где особенно нужна внимательная проверка. Он не "
        "утверждает, что в вопросе уже есть ошибка.",
        "",
        "## Как вернуть замечания",
        "",
        "Из-за ненадёжной передачи вложений замечания нужно вставлять прямо в "
        "тело сообщения, а не присылать отдельным файлом. Один блок обратной "
        "связи оформляется так:",
        "",
        "```text",
        f"Версии: content {_short(content_commit)}; app {_short(app_commit)}",
        "Проверенный блок: Л01–Л10",
        "ID: Л06.2",
        "Уровень: BLOCKER / MAJOR / MINOR / STYLE",
        "Поле: вопрос / ответ A–C / объяснение / исключение",
        "Проблема:",
        "Предлагаемая правка:",
        "Основание или источник:",
        "Итог блока: проверен полностью; иных богословских замечаний нет.",
        "```",
        "",
        "Уровни: `BLOCKER` — догматическая или пастырски опасная ошибка; "
        "`MAJOR` — существенное искажение смысла; `MINOR` — локальная неточность "
        "или двусмысленность; `STYLE` — редактура без изменения смысла.",
        "",
        "## Устройство файлов",
        "",
        "В каждой главе приведены риск-теги, короткий начальный фрагмент "
        "первоисточника, три вопроса со всеми вариантами, ключом и объяснением, "
        "а также пустые поля вердикта. Для проверки контекста следует переходить "
        "по ссылке на полный источник в начале файла книги.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def render_packet(
    content_root: Path,
    app_root: Path,
    content_commit: str,
    app_commit: str,
) -> dict[str, str]:
    books = load_books(content_root, app_root, content_commit, app_commit)
    rendered = {
        "00_README.md": _render_readme(books, content_commit, app_commit),
    }
    rendered.update({book.filename: _render_book(book) for book in books})
    return rendered


def write_packet(output_dir: Path, rendered: dict[str, str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in sorted(rendered):
        path = output_dir / filename
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered[filename])


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content-root", type=Path, default=CONTENT_ROOT)
    parser.add_argument("--app-root", type=Path, default=DEFAULT_APP_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--content-commit",
        help="input commit id; defaults to the content repository HEAD",
    )
    parser.add_argument(
        "--app-commit",
        help="input commit id; defaults to the app repository HEAD",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    content_root = args.content_root.resolve()
    app_root = args.app_root.resolve()
    content_commit = args.content_commit or _git_head(content_root)
    app_commit = args.app_commit or _git_head(app_root)
    rendered = render_packet(
        content_root=content_root,
        app_root=app_root,
        content_commit=content_commit,
        app_commit=app_commit,
    )
    write_packet(args.output_dir.resolve(), rendered)
    total_bytes = sum(len(value.encode("utf-8")) for value in rendered.values())
    print(
        f"Wrote {len(rendered)} files to {args.output_dir.resolve()} "
        f"({total_bytes} bytes)"
    )


if __name__ == "__main__":
    main()
