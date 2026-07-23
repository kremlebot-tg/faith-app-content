#!/usr/bin/env python3
"""Build a deterministic theological review packet for Ignatius tests."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

if __package__:
    from tools import build_damaskin_review_packet as common
else:
    import build_damaskin_review_packet as common


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reviews" / "ignatij_prinoshenie"
BOOK_ID = "ignatij_prinoshenie"
CHAPTER_COUNT = 60
QUESTION_COUNT = 180
CHUNK_SIZE = 15


def _risk_tags() -> dict[int, tuple[str, ...]]:
    tags: dict[int, list[str]] = {
        number: ["монашеский адресат и границы применения"]
        for number in range(1, CHAPTER_COUNT + 1)
    }

    def add(numbers: list[int] | range, label: str) -> None:
        for number in numbers:
            tags[number].append(label)

    add([1, 3, 11, 12, 24, 45, 46, 50, 59], "перенос монашеского правила на мирян")
    add([1, 11, 12, 38, 44], "послушание, власть наставника и совесть")
    add([13, 16, 27, 30, 36, 40, 41, 45, 48], "насилие, безопасность и границы")
    add(range(17, 25), "мера молитвенного и телесного подвига")
    add([21, 23, 24, 25, 31, 35, 42, 51, 52, 53, 54, 56], "помыслы, прелесть и тревожность")
    add([26, 33, 58, 60], "отчаяние, самоповреждение и надежда")
    add([28, 51, 54], "эсхатология, падшие духи и суеверие")
    add([29, 34, 37], "Промысл, страдание и недопустимость обвинения пострадавшего")
    add([32, 39, 58, 60], "смирение, достоинство личности и самоукорение")
    add([43, 46, 47, 49], "аскеза, нестяжание и жизнь в миру")
    add([50, 57], "исторические гендерные формулировки")
    add([59, 60], "жанр, адресат и исторический контекст")
    return {number: tuple(values) for number, values in tags.items()}


RISK_TAGS = _risk_tags()


def render_index(
    book: dict[str, Any],
    commit: str,
    source_sha: str,
    drafts_sha: str,
) -> str:
    return f"""<!-- ignatius-review-packet: content={commit} -->
# Богословская рецензия тестов к книге «{book['work']}»

Пакет фиксирует полный комплект: {CHAPTER_COUNT} глав и {QUESTION_COUNT}
вопросов. Он предназначен для проверки соответствия первоисточнику,
богословской точности, пастырской безопасности и качества дистракторов.
Публиковать тесты до получения человеческого вердикта не следует.

- Входной commit: `{commit}`
- SHA-256 книги: `{source_sha}`
- SHA-256 комплекта черновиков: `{drafts_sha}`
- Источник: [{book['source']}]({book['source']})
- Редакторские предостережения: [00_README.md](00_README.md)

## Файлы

- [01_chapters_001_015.md](01_chapters_001_015.md) — главы 1–15.
- [02_chapters_016_030.md](02_chapters_016_030.md) — главы 16–30.
- [03_chapters_031_045.md](03_chapters_031_045.md) — главы 31–45.
- [04_chapters_046_060.md](04_chapters_046_060.md) — главы 46–60.

## Что проверять

1. Следует ли ключ точному смыслу главы и православному вероучению.
2. Не говорит ли объяснение больше, чем позволяет первоисточник.
3. Остаётся ли каждый дистрактор однозначно неверным, но правдоподобным.
4. Не превращено ли монашеское наставление в обязательное правило для мирян.
5. Учтено ли предостережение для конкретной главы из `00_README.md`.
6. Не создаёт ли формулировка риска для человека в состоянии тревоги,
   отчаяния, болезни, насилия или духовной неопытности.

## Как вернуть замечания

Из-за ненадёжной передачи вложений замечания нужно вставлять прямо в тело
сообщения. Формат одного замечания:

```text
Версия: content {commit[:7]}
Проверенный блок: ИП001–ИП015
ID: ИП021.2
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


def render_chunk(
    book: dict[str, Any],
    chapters: list[dict[str, Any]],
    tests: dict[int, list[dict[str, Any]]],
    commit: str,
    source_sha: str,
    drafts_sha: str,
) -> str:
    review_chapters = []
    for chapter in chapters:
        review_chapter = dict(chapter)
        paragraphs = list(chapter.get("paragraphs", []))
        if paragraphs:
            heading = str(paragraphs[0]).strip().casefold().replace("e", "е")
            if heading == "введение":
                paragraphs = paragraphs[1:]
        review_chapter["paragraphs"] = paragraphs
        review_chapters.append(review_chapter)
    rendered = common.render_chunk(
        book,
        review_chapters,
        tests,
        commit,
        source_sha,
        drafts_sha,
        risk_tags=RISK_TAGS,
    )
    return rendered.replace("ИД", "ИП")


def render_packet(
    book_path: Path,
    drafts_dir: Path,
    commit: str,
) -> dict[str, str]:
    book = common.load_json(book_path)
    chapters = book.get("chapters", [])
    if book.get("id") != BOOK_ID:
        raise ValueError(f"Ожидается книга {BOOK_ID}")
    if book.get("chapters_count") != len(chapters):
        raise ValueError("chapters_count не совпадает с фактическим числом глав")
    chapter_numbers = [int(chapter["number"]) for chapter in chapters]
    if chapter_numbers != list(range(1, CHAPTER_COUNT + 1)):
        raise ValueError(f"Ожидаются главы 1–{CHAPTER_COUNT} без пропусков")

    tests, draft_paths = common.load_drafts(
        drafts_dir=drafts_dir,
        book_id=BOOK_ID,
        expected_numbers=set(chapter_numbers),
    )
    source_sha = common.sha256(book_path)
    drafts_sha = common.combined_sha256(draft_paths)
    rendered = {
        "00_PACKET.md": render_index(book, commit, source_sha, drafts_sha),
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", type=Path, default=ROOT / f"{BOOK_ID}.json")
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
