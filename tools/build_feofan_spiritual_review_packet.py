#!/usr/bin/env python3
"""Build a deterministic review packet for Feofan's Spiritual Life tests."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

if __package__:
    from tools import build_damaskin_review_packet as common
else:
    import build_damaskin_review_packet as common


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reviews" / "feofan_dukhovnaja_zhizn"
BOOK_ID = "feofan_dukhovnaja_zhizn"
CHAPTER_COUNT = 80
QUESTION_COUNT = 240
CHUNK_SIZE = 20


def _risk_tags() -> dict[int, tuple[str, ...]]:
    tags: dict[int, list[str]] = {
        number: ["соответствие смыслу письма и пастырская ясность"]
        for number in range(1, CHAPTER_COUNT + 1)
    }

    def add(numbers: list[int] | range, label: str) -> None:
        for number in numbers:
            tags[number].append(label)

    add(range(1, 13), "христианская антропология и границы психологических обобщений")
    add([10, 13, 14, 27], "исторические естественно-научные представления")
    add([15], "молитва святым и различение дара и усилия")
    add([17, 63, 70], "культура, образование и историческая полемика")
    add(range(19, 23), "грехопадение, благодать, свобода и действие Святой Троицы")
    add(range(25, 30), "Крещение, благодать и свободный ответ человека")
    add([30, 37, 44, 60, 75], "покаяние, отчаяние и надежда")
    add(range(31, 45), "духовное руководство, рассуждение и мера подвига")
    add(range(45, 49), "молитвенное правило, внимание и отсутствие магизма")
    add(range(49, 53), "Промысл, повседневные обязанности и духовное чувство")
    add(range(53, 63), "помыслы, согласие, вина и тревожная скрупулёзность")
    add([56], "гнев, защита ближнего и недопустимость мести")
    add([61, 64, 69, 79], "психическое состояние, безопасность и обращение за помощью")
    add([67], "исповедь, сокрытый грех и риск отчаяния")
    add([68, 69], "духовный совет, совесть и ложные откровения")
    add(range(72, 76), "призвание, безбрачие и достоинство брака")
    add([76], "апологетика и устаревшие научные аргументы")
    add([77, 78], "послушание родителям, насилие и безопасный выход")
    return {number: tuple(values) for number, values in tags.items()}


RISK_TAGS = _risk_tags()


def embedded_tests(book: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    return {
        int(chapter["number"]): chapter["test"]
        for chapter in book.get("chapters", [])
        if chapter.get("test")
    }


def consolidated_tests(path: Path) -> dict[int, list[dict[str, Any]]]:
    data = common.load_json(path)
    if data.get("book_id") != BOOK_ID:
        raise ValueError(f"{path.name}: неверный book_id")
    result: dict[int, list[dict[str, Any]]] = {}
    for chapter in data.get("chapters", []):
        number = int(chapter["number"])
        if number in result:
            raise ValueError(f"{path.name}: глава {number} повторяется")
        result[number] = chapter["test"]
    return result


def render_index(
    book: dict[str, Any],
    commit: str,
    source_sha: str,
    consolidated_sha: str,
    drafts_sha: str,
) -> str:
    return f"""<!-- feofan-spiritual-review-packet: content={commit} -->
# Богословская рецензия тестов к книге «{book['work']}»

Пакет фиксирует опубликованный комплект: {CHAPTER_COUNT} писем и
{QUESTION_COUNT} вопросов. Генератор подтвердил полное совпадение тестов в
черновиках, объединённом файле и книге. Пакет предназначен для
постпубликационной человеческой проверки богословской точности, пастырской
безопасности и ясности.

- Входной commit: `{commit}`
- Версия книги: `{book['version']}`
- SHA-256 книги: `{source_sha}`
- SHA-256 объединённого файла тестов: `{consolidated_sha}`
- SHA-256 комплекта черновиков: `{drafts_sha}`
- Источник: [{book['source']}]({book['source']})

## Файлы

- [01_letters_001_020.md](01_letters_001_020.md) — письма 1–20.
- [02_letters_021_040.md](02_letters_021_040.md) — письма 21–40.
- [03_letters_041_060.md](03_letters_041_060.md) — письма 41–60.
- [04_letters_061_080.md](04_letters_061_080.md) — письма 61–80.

## Что проверять

1. Следует ли ключ точному смыслу письма и православному вероучению.
2. Не говорит ли объяснение больше, чем позволяет первоисточник.
3. Остаётся ли каждый дистрактор однозначно неверным, но правдоподобным.
4. Не подано ли историческое естественно-научное мнение как догмат.
5. Не усиливает ли формулировка скрупулёзность, отчаяние или страх.
6. Не превращены ли советы конкретной адресатке в безусловное правило.
7. Сохранены ли границы родительской и духовной власти, безопасность и право
   обратиться за помощью.

## Как вернуть замечания

Из-за ненадёжной передачи вложений замечания нужно вставлять прямо в тело
сообщения:

```text
Версия: content {commit[:7]}; книга v{book['version']}
Проверенный блок: ФД001–ФД020
ID: ФД021.2
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
    tests_path: Path,
    drafts_dir: Path,
    commit: str,
) -> dict[str, str]:
    book = common.load_json(book_path)
    chapters = book.get("chapters", [])
    if book.get("id") != BOOK_ID:
        raise ValueError(f"Ожидается книга {BOOK_ID}")
    if book.get("chapters_count") != len(chapters):
        raise ValueError("chapters_count не совпадает с фактическим числом писем")
    numbers = [int(chapter["number"]) for chapter in chapters]
    if numbers != list(range(1, CHAPTER_COUNT + 1)):
        raise ValueError(f"Ожидаются письма 1–{CHAPTER_COUNT} без пропусков")

    book_tests = embedded_tests(book)
    merged_tests = consolidated_tests(tests_path)
    draft_tests, draft_paths = common.load_drafts(
        drafts_dir,
        BOOK_ID,
        set(numbers),
    )
    if book_tests != merged_tests or book_tests != draft_tests:
        raise ValueError(
            "Тесты в книге, объединённом файле и черновиках не совпадают"
        )

    source_sha = common.sha256(book_path)
    tests_sha = common.sha256(tests_path)
    drafts_sha = common.combined_sha256(draft_paths)
    rendered = {
        "00_PACKET.md": render_index(
            book,
            commit,
            source_sha,
            tests_sha,
            drafts_sha,
        ),
    }
    for chunk_index, start in enumerate(
        range(0, len(chapters), CHUNK_SIZE),
        start=1,
    ):
        chunk = chapters[start : start + CHUNK_SIZE]
        first = int(chunk[0]["number"])
        last = int(chunk[-1]["number"])
        filename = f"{chunk_index:02d}_letters_{first:03d}_{last:03d}.md"
        content = common.render_chunk(
            book,
            chunk,
            book_tests,
            commit,
            source_sha,
            drafts_sha,
            risk_tags=RISK_TAGS,
        )
        rendered[filename] = (
            content.replace("ИД", "ФД")
            .replace(" · главы ", " · письма ")
            .replace("Фрагмент главы", "Фрагмент письма")
        )
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", type=Path, default=ROOT / f"{BOOK_ID}.json")
    parser.add_argument(
        "--tests",
        type=Path,
        default=ROOT / "content_tests" / f"{BOOK_ID}.json",
    )
    parser.add_argument(
        "--drafts-dir",
        type=Path,
        default=ROOT / "content_tests" / "drafts",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--content-commit")
    args = parser.parse_args()
    commit = args.content_commit or common.git_head(ROOT)
    rendered = render_packet(
        args.book.resolve(),
        args.tests.resolve(),
        args.drafts_dir.resolve(),
        commit,
    )
    common.write_packet(args.output_dir.resolve(), rendered)
    total_bytes = sum(len(value.encode("utf-8")) for value in rendered.values())
    print(
        f"Wrote {len(rendered)} files to {args.output_dir.resolve()} "
        f"({total_bytes} bytes)"
    )


if __name__ == "__main__":
    main()
