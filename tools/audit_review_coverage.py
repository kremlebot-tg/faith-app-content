#!/usr/bin/env python3
"""Audit theological review-packet coverage and render a central registry."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "reviews" / "00_REGISTRY.md"
VERDICT_MARKER = "**Вердикт:**"


@dataclass(frozen=True)
class ReviewCoverage:
    book_id: str
    prefix: str
    test_status: str
    expected_questions: int
    files: tuple[str, ...]


COVERAGE = (
    ReviewCoverage(
        "afanasij_voploshhenie",
        "АВ",
        "опубликованы",
        27,
        ("reviews/early_fathers/01_afanasij.md",),
    ),
    ReviewCoverage(
        "makarij_duhovnye_besedy",
        "МБ",
        "опубликованы",
        150,
        (
            "reviews/early_fathers/02_makarij_001_025.md",
            "reviews/early_fathers/03_makarij_026_050.md",
        ),
    ),
    ReviewCoverage(
        "ioann_zlatoust_pokajanie",
        "ИЗ",
        "опубликованы",
        27,
        ("reviews/early_fathers/04_zlatoust.md",),
    ),
    ReviewCoverage(
        "avva_dorofey",
        "Д",
        "опубликованы",
        63,
        ("reviews/v1.3.1/03_avva_dorofey.md",),
    ),
    ReviewCoverage(
        "ioann_lestvichnik",
        "Л",
        "опубликованы",
        90,
        ("reviews/v1.3.1/01_lestvitsa.md",),
    ),
    ReviewCoverage(
        "ioann_damaskin",
        "ИД",
        "черновики, не опубликованы",
        300,
        (
            "reviews/ioann_damaskin/01_chapters_001_025.md",
            "reviews/ioann_damaskin/02_chapters_026_050.md",
            "reviews/ioann_damaskin/03_chapters_051_075.md",
            "reviews/ioann_damaskin/04_chapters_076_100.md",
        ),
    ),
    ReviewCoverage(
        "feofan_put_ko_spaseniyu",
        "Ф",
        "опубликованы",
        84,
        ("reviews/v1.3.1/02_feofan.md",),
    ),
    ReviewCoverage(
        "feofan_dukhovnaja_zhizn",
        "ФД",
        "опубликованы",
        240,
        (
            "reviews/feofan_dukhovnaja_zhizn/01_letters_001_020.md",
            "reviews/feofan_dukhovnaja_zhizn/02_letters_021_040.md",
            "reviews/feofan_dukhovnaja_zhizn/03_letters_041_060.md",
            "reviews/feofan_dukhovnaja_zhizn/04_letters_061_080.md",
        ),
    ),
    ReviewCoverage(
        "ignatij_prinoshenie",
        "ИП",
        "черновики, не опубликованы",
        180,
        (
            "reviews/ignatij_prinoshenie/01_chapters_001_015.md",
            "reviews/ignatij_prinoshenie/02_chapters_016_030.md",
            "reviews/ignatij_prinoshenie/03_chapters_031_045.md",
            "reviews/ignatij_prinoshenie/04_chapters_046_060.md",
        ),
    ),
)


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


def count_source_questions(root: Path, entry: ReviewCoverage) -> int:
    book_path = root / f"{entry.book_id}.json"
    if book_path.exists():
        book = load_json(book_path)
        embedded = sum(
            len(chapter.get("test", []))
            for chapter in book.get("chapters", [])
        )
        if embedded:
            return embedded

    total = 0
    seen: set[int] = set()
    for path in sorted(
        (root / "content_tests" / "drafts").glob(f"{entry.book_id}_*.json")
    ):
        data = load_json(path)
        if data.get("book_id") != entry.book_id:
            raise ValueError(f"{path.name}: неверный book_id")
        for chapter in data.get("chapters", []):
            number = int(chapter["number"])
            if number in seen:
                raise ValueError(f"{entry.book_id}: глава {number} повторяется")
            seen.add(number)
            total += len(chapter.get("test", []))
    return total


def packet_stats(
    root: Path,
    entry: ReviewCoverage,
) -> tuple[int, set[str]]:
    verdicts = 0
    ids: set[str] = set()
    id_pattern = re.compile(
        rf"^### ({re.escape(entry.prefix)}\d{{2,3}}\.[1-3])$",
        re.MULTILINE,
    )
    for filename in entry.files:
        path = root / filename
        if not path.is_file():
            raise ValueError(f"{entry.book_id}: нет файла {filename}")
        text = path.read_text(encoding="utf-8")
        verdicts += text.count(VERDICT_MARKER)
        found = id_pattern.findall(text)
        duplicate_ids = ids.intersection(found)
        if duplicate_ids:
            raise ValueError(
                f"{entry.book_id}: повторяются ID {sorted(duplicate_ids)}"
            )
        ids.update(found)
    return verdicts, ids


def audit(root: Path) -> dict[str, tuple[int, int]]:
    manifest = load_json(root / "manifest.json")
    manifest_ids = {
        str(book["id"])
        for book in manifest.get("library", [])
    }
    configured_ids = {entry.book_id for entry in COVERAGE}
    if manifest_ids != configured_ids:
        missing = sorted(manifest_ids - configured_ids)
        extra = sorted(configured_ids - manifest_ids)
        raise ValueError(
            f"Реестр не совпадает с manifest: пропущены={missing}, лишние={extra}"
        )

    result: dict[str, tuple[int, int]] = {}
    for entry in COVERAGE:
        source_questions = count_source_questions(root, entry)
        verdicts, ids = packet_stats(root, entry)
        if source_questions != entry.expected_questions:
            raise ValueError(
                f"{entry.book_id}: в источнике {source_questions} вопросов, "
                f"ожидалось {entry.expected_questions}"
            )
        if verdicts != entry.expected_questions:
            raise ValueError(
                f"{entry.book_id}: в пакете {verdicts} полей вердикта, "
                f"ожидалось {entry.expected_questions}"
            )
        if len(ids) != entry.expected_questions:
            raise ValueError(
                f"{entry.book_id}: найдено {len(ids)} уникальных ID, "
                f"ожидалось {entry.expected_questions}"
            )
        result[entry.book_id] = (source_questions, verdicts)
    return result


def render_registry(root: Path, commit: str) -> str:
    manifest = load_json(root / "manifest.json")
    books = {
        str(book["id"]): book
        for book in manifest.get("library", [])
    }
    rows = []
    for entry in COVERAGE:
        book = books[entry.book_id]
        links = "<br>".join(
            f"[{Path(filename).name}]({Path(filename).relative_to('reviews')})"
            for filename in entry.files
        )
        rows.append(
            f"| {book['author']} · «{book['work']}» | {entry.test_status} | "
            f"{entry.expected_questions} | {links} | ожидается |"
        )

    published = sum(
        entry.expected_questions
        for entry in COVERAGE
        if entry.test_status == "опубликованы"
    )
    drafts = sum(
        entry.expected_questions
        for entry in COVERAGE
        if entry.test_status != "опубликованы"
    )
    return f"""<!-- review-coverage-registry: content={commit} -->
# Реестр богословской рецензии тестов

Реестр охватывает все девять книг из `manifest.json`: {published}
опубликованный вопрос и {drafts} вопросов в черновиках. Для каждого вопроса
существует стабильный ID и отдельное поле вердикта.

Наличие пакета не означает, что рецензия завершена. Пока заполненный вердикт
богословски грамотного человека не зафиксирован в репозитории, статус
человеческой рецензии остаётся «ожидается».

- Входной commit: `{commit}`
- Всего подготовлено к проверке: {published + drafts} вопросов.

| Книга | Статус тестов | Вопросы | Пакет | Человеческая рецензия |
|---|---|---:|---|---|
{chr(10).join(rows)}

## Контроль

```sh
python3 tools/audit_review_coverage.py
```

Аудитор требует, чтобы каждая книга манифеста присутствовала в реестре, число
вопросов совпадало с исходными JSON или полным комплектом черновиков, а пакет
содержал ровно по одному уникальному ID и полю вердикта на вопрос.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write-registry", action="store_true")
    parser.add_argument("--content-commit")
    args = parser.parse_args()
    root = args.root.resolve()
    result = audit(root)
    total = sum(source for source, _ in result.values())
    print(f"books={len(result)} questions={total} review_fields={total} errors=0")
    if args.write_registry:
        commit = args.content_commit or git_head(root)
        path = root / "reviews" / "00_REGISTRY.md"
        path.write_text(
            render_registry(root, commit),
            encoding="utf-8",
            newline="\n",
        )
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
