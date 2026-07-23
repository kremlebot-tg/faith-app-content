#!/usr/bin/env python3
"""Build a deterministic theological review packet for Damascene tests."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reviews" / "ioann_damaskin"
CHUNK_SIZE = 25
EXCERPT_LIMIT = 600


RISK_TAGS: dict[int, tuple[str, ...]] = {
    **{number: ("Троица и Божественные свойства",) for number in range(1, 15)},
    **{number: ("творение, Промысл и свобода",) for number in range(15, 44)},
    **{number: ("христология и ипостасное соединение",) for number in range(44, 82)},
    82: ("Крещение и действие благодати",),
    83: ("вера и христианская жизнь",),
    84: ("Крест и границы почитания святыни",),
    85: ("Предание и телесное участие в молитве",),
    86: ("Евхаристия и достойное причащение",),
    87: ("Богородица и приснодевство",),
    88: ("почитание святых и мощей",),
    89: ("иконопочитание и отличие от идолопоклонства",),
    90: ("Писание, канон и внешняя литература",),
    91: ("христологические речения и свойства природ",),
    92: ("Бог, зло и Божие попущение",),
    93: ("происхождение зла и свобода дьявола",),
    94: ("предведение Бога и свобода человека",),
    95: ("грех, телесность, благодать и молитва",),
    96: ("Ветхий Завет, суббота и антииудейская риторика",),
    97: ("брак, девство и свобода призвания",),
    98: ("обрезание, Крещение и исполнение закона",),
    99: ("антихрист, иудеи и эсхатология",),
    100: ("воскресение тела, Суд и вечная участь",),
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: ожидается JSON-объект")
    return value


def git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_drafts(
    drafts_dir: Path,
    book_id: str,
    expected_numbers: set[int],
) -> tuple[dict[int, list[dict[str, Any]]], list[Path]]:
    paths = sorted(drafts_dir.glob(f"{book_id}_*.json"))
    if not paths:
        raise ValueError(f"Не найдены черновики {book_id}")

    tests: dict[int, list[dict[str, Any]]] = {}
    for path in paths:
        source = load_json(path)
        if source.get("book_id") != book_id:
            raise ValueError(f"{path.name}: неверный book_id")
        for chapter in source.get("chapters", []):
            number = chapter.get("number")
            if not isinstance(number, int):
                raise ValueError(f"{path.name}: неверный номер главы {number!r}")
            if number in tests:
                raise ValueError(f"Глава {number} повторяется")
            questions = chapter.get("test")
            if not isinstance(questions, list) or len(questions) != 3:
                raise ValueError(f"Глава {number}: требуется ровно три вопроса")
            for index, question in enumerate(questions, start=1):
                answers = question.get("answers")
                if not isinstance(answers, list) or len(answers) != 3:
                    raise ValueError(
                        f"Глава {number}, вопрос {index}: требуется три ответа"
                    )
                if sum(answer.get("correct") is True for answer in answers) != 1:
                    raise ValueError(
                        f"Глава {number}, вопрос {index}: неверное число ключей"
                    )
                if not str(question.get("explanation", "")).strip():
                    raise ValueError(
                        f"Глава {number}, вопрос {index}: нет объяснения"
                    )
            tests[number] = questions

    if set(tests) != expected_numbers:
        missing = sorted(expected_numbers - set(tests))
        extra = sorted(set(tests) - expected_numbers)
        raise ValueError(f"Неполное покрытие: пропущены={missing}, лишние={extra}")
    return tests, paths


def combined_sha256(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def source_excerpt(chapter: dict[str, Any]) -> str:
    paragraph = next(
        (
            str(value).strip()
            for value in chapter.get("paragraphs", [])
            if str(value).strip()
        ),
        "",
    )
    if not paragraph:
        raise ValueError(f"Глава {chapter.get('number')}: нет текста")
    if len(paragraph) <= EXCERPT_LIMIT:
        return paragraph
    boundary = paragraph[: EXCERPT_LIMIT + 1].rfind(" ")
    return paragraph[: boundary if boundary > 0 else EXCERPT_LIMIT].rstrip() + "…"


def answer_label(index: int) -> str:
    return "ABC"[index]


def render_chunk(
    book: dict[str, Any],
    chapters: list[dict[str, Any]],
    tests: dict[int, list[dict[str, Any]]],
    commit: str,
    source_sha: str,
    drafts_sha: str,
    risk_tags: dict[int, tuple[str, ...]] = RISK_TAGS,
    chapter_notes: dict[int, str] | None = None,
) -> str:
    first = int(chapters[0]["number"])
    last = int(chapters[-1]["number"])
    lines = [
        f"# {book['work']} · главы {first}–{last}",
        "",
        f"- Автор: {book['author']}",
        f"- Входной commit: `{commit}`",
        f"- SHA-256 книги: `{source_sha}`",
        f"- SHA-256 комплекта черновиков: `{drafts_sha}`",
        f"- Источник: [{book['source']}]({book['source']})",
        "",
        "Фрагмент главы служит для быстрой ориентации и не заменяет чтение "
        "полного текста. Вопросы, ответы и объяснения перенесены без правок.",
        "",
    ]
    for chapter in chapters:
        number = int(chapter["number"])
        chapter_id = f"ИД{number:03d}"
        tags = risk_tags.get(number, ("общая богословская точность",))
        lines.extend(
            [
                f"## {chapter_id} · {chapter['title']}",
                "",
                "**Риск-теги:** " + "; ".join(f"`{tag}`" for tag in tags),
                "",
            ]
        )
        note = (chapter_notes or {}).get(number)
        if note:
            lines.extend(
                [
                    f"**Редакторская оговорка:** {note}",
                    "",
                ]
            )
        lines.extend(
            [
                "**Фрагмент источника:**",
                "",
                f"> {source_excerpt(chapter)}",
                "",
            ]
        )
        for question_index, question in enumerate(tests[number], start=1):
            correct_index = next(
                index
                for index, answer in enumerate(question["answers"])
                if answer["correct"] is True
            )
            lines.extend(
                [
                    f"### {chapter_id}.{question_index}",
                    "",
                    f"**Вопрос:** {question['question']}",
                    "",
                ]
            )
            for answer_index, answer in enumerate(question["answers"]):
                lines.append(f"- {answer_label(answer_index)}. {answer['text']}")
            lines.extend(
                [
                    "",
                    f"**Ключ:** {answer_label(correct_index)}",
                    "",
                    f"**Объяснение:** {question['explanation']}",
                    "",
                    "**Вердикт:** ☐ принять ☐ исправить ☐ снять вопрос",
                    "",
                    "**Замечание / предлагаемая правка / источник:**",
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


def render_readme(
    book: dict[str, Any],
    commit: str,
    source_sha: str,
    drafts_sha: str,
) -> str:
    return f"""<!-- damaskin-review-packet: content={commit} -->
# Богословская рецензия тестов к книге «{book['work']}»

Пакет фиксирует полный комплект: 100 глав и 300 вопросов. Он предназначен для
проверки ключей, объяснений, границ святоотеческой мысли и пастырской ясности.
Публиковать тесты до получения человеческого вердикта не следует.

- Входной commit: `{commit}`
- SHA-256 книги: `{source_sha}`
- SHA-256 комплекта черновиков: `{drafts_sha}`
- Источник: [{book['source']}]({book['source']})

## Файлы

- [01_chapters_001_025.md](01_chapters_001_025.md) — главы 1–25.
- [02_chapters_026_050.md](02_chapters_026_050.md) — главы 26–50.
- [03_chapters_051_075.md](03_chapters_051_075.md) — главы 51–75.
- [04_chapters_076_100.md](04_chapters_076_100.md) — главы 76–100.

## Что проверять

1. Следует ли ключ точному смыслу главы и православному вероучению.
2. Не говорит ли объяснение больше, чем позволяет первоисточник.
3. Остаётся ли каждый дистрактор однозначно неверным, но правдоподобным.
4. Не создаёт ли сокращение догматической двусмысленности.
5. Не требует ли историческая полемика пастырского пояснения для современного
   читателя, особенно в главах 96 и 99.

## Как вернуть замечания

Из-за ненадёжной передачи вложений замечания нужно вставлять прямо в тело
сообщения. Формат одного замечания:

```text
Версия: content {commit[:7]}
Проверенный блок: ИД001–ИД025
ID: ИД044.2
Уровень: BLOCKER / MAJOR / MINOR / STYLE
Поле: вопрос / ответ A–C / объяснение
Проблема:
Предлагаемая правка:
Основание или источник:
Итог блока: проверен полностью; иных богословских замечаний нет.
```

`BLOCKER` означает догматическую или пастырски опасную ошибку, `MAJOR` —
существенное искажение, `MINOR` — локальную неточность, `STYLE` — редактуру
без изменения смысла.
"""


def render_packet(
    book_path: Path,
    drafts_dir: Path,
    commit: str,
) -> dict[str, str]:
    book = load_json(book_path)
    chapters = book.get("chapters", [])
    if book.get("id") != "ioann_damaskin":
        raise ValueError("Ожидается книга ioann_damaskin")
    if book.get("chapters_count") != len(chapters):
        raise ValueError("chapters_count не совпадает с фактическим числом глав")
    chapter_numbers = [int(chapter["number"]) for chapter in chapters]
    if chapter_numbers != list(range(1, 101)):
        raise ValueError("Ожидаются главы 1–100 без пропусков")

    tests, draft_paths = load_drafts(
        drafts_dir=drafts_dir,
        book_id=book["id"],
        expected_numbers=set(chapter_numbers),
    )
    source_sha = sha256(book_path)
    drafts_sha = combined_sha256(draft_paths)
    rendered = {
        "00_README.md": render_readme(book, commit, source_sha, drafts_sha),
    }
    for chunk_index, start in enumerate(
        range(0, len(chapters), CHUNK_SIZE),
        start=1,
    ):
        chunk = chapters[start : start + CHUNK_SIZE]
        first = int(chunk[0]["number"])
        last = int(chunk[-1]["number"])
        filename = f"{chunk_index:02d}_chapters_{first:03d}_{last:03d}.md"
        rendered[filename] = render_chunk(
            book,
            chunk,
            tests,
            commit,
            source_sha,
            drafts_sha,
        )
    return rendered


def write_packet(output_dir: Path, rendered: dict[str, str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in sorted(rendered.items()):
        (output_dir / filename).write_text(content, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", type=Path, default=ROOT / "ioann_damaskin.json")
    parser.add_argument(
        "--drafts-dir",
        type=Path,
        default=ROOT / "content_tests" / "drafts",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--content-commit")
    args = parser.parse_args()
    commit = args.content_commit or git_head(ROOT)
    rendered = render_packet(
        args.book.resolve(),
        args.drafts_dir.resolve(),
        commit,
    )
    write_packet(args.output_dir.resolve(), rendered)
    total_bytes = sum(len(value.encode("utf-8")) for value in rendered.values())
    print(
        f"Wrote {len(rendered)} files to {args.output_dir.resolve()} "
        f"({total_bytes} bytes)"
    )


if __name__ == "__main__":
    main()
