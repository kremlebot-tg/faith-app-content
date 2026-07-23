#!/usr/bin/env python3
"""Build a deterministic review packet for three released patristic books."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__:
    from tools import build_damaskin_review_packet as common
else:
    import build_damaskin_review_packet as common


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reviews" / "early_fathers"


@dataclass(frozen=True)
class ReviewConfig:
    book_id: str
    prefix: str
    filename: str
    first: int
    last: int
    unit_plural: str
    risk_tags: dict[int, tuple[str, ...]]


AFANASIJ_RISKS = {
    1: ("творение, образ Божий, грехопадение и свобода",),
    2: ("Воплощение, тление и границы юридических метафор",),
    3: ("Воплощение, тление и восстановление образа",),
    4: ("Крест, искупление и добровольность смерти Христа",),
    5: ("Воскресение Христа и свидетельство Церкви",),
    6: ("историческая антииудейская полемика",),
    7: ("апологетика и исторические представления о язычестве",),
    8: ("апологетика и исторические представления о язычестве",),
    9: ("границы апологетического аргумента",),
}

MAKARIJ_RISKS = {
    **{
        number: ("традиционная атрибуция корпуса",)
        for number in range(1, 51)
    },
    1: ("аллегорическое толкование Писания и действие Святого Духа",),
    2: ("грех, падшие духи и свобода человека",),
    3: ("братская любовь, помыслы и монашеский адресат",),
    4: ("аскеза, мирская жизнь и границы применения",),
    5: ("аскеза, мирская жизнь и границы применения",),
    6: ("молитва, соблазн ближнего и эсхатологические образы",),
    7: ("Воплощение и снисхождение Христа",),
    8: ("духовное совершенство и недопустимость самоуверенности",),
    9: ("искушение, Промысл и свобода",),
    10: ("благодать, смирение и утрата дара",),
    11: ("типология Креста, падшие духи и образный диалог",),
    12: ("образ Божий, грехопадение и достоинство человека",),
    14: ("Таинства, благодать и невидимые духовные образы",),
    15: ("воскресение тела, зло, благодать и свобода",),
    16: ("искушение, первородный грех и личная ответственность",),
    17: ("Христос, спасение и духовное помазание",),
    18: ("Христос, Святой Дух и степени духовного роста",),
    19: ("благодать, понуждение себя и опасность самооправдания",),
    20: ("Христос как врач и действие благодати",),
    21: ("помыслы, падшие духи и монашеское удаление от мира",),
    22: ("смерть, посмертная участь и пастырская надежда",),
    24: ("первородный грех, Христос и образ закваски",),
    25: ("Крест, страсти, слёзы и мера аскезы",),
    26: ("достоинство души, искушение и свобода",),
    27: ("благодать, свобода и ответственность",),
    28: ("плач о душе без усиления отчаяния",),
    29: ("благодать, плод и Суд без идеи заслуживания",),
    30: ("рождение от Святого Духа",),
    31: ("собирание ума и риск молитвенной скрупулёзности",),
    32: ("воскресение тела и слава благодати",),
    33: ("непрестанная молитва и мера начинающего",),
    34: ("воскресение тела и различие славы",),
    35: ("Ветхий Завет, суббота и историческая полемика",),
    36: ("воскресение души и тела, Суд и вечная участь",),
    37: ("рай и духовное толкование закона",),
    38: ("различение духовного состояния без осуждения",),
    39: ("назначение и толкование Священного Писания",),
    40: ("связь навыков без отрицания свободы и покаяния",),
    41: ("рост благодати и порока без фатализма",),
    42: ("благодать, зло и границы внутреннего самоанализа",),
    43: ("сердце и недопустимость сведения веры к переживаниям",),
    44: ("обновление во Христе и исцеление страстей",),
    45: ("исцеление Христом и обожение без смешения природ",),
    46: ("риторика о мире без презрения к людям",),
    47: ("аллегория Ветхого Завета и историческая полемика",),
    48: ("вера, доверие Богу и человеческая ответственность",),
    49: ("отречение, земные блага и монашеский адресат",),
    50: ("чудеса святых и недопустимость суеверия",),
}

ZLATOUST_RISKS = {
    1: ("покаяние, надежда и недопустимость отчаяния",),
    2: ("покаяние, наказание и исторические примеры",),
    3: ("милостыня, добрые дела и отсутствие идеи заслуживания",),
    4: ("покаяние, молитва и милосердие Бога",),
    5: ("пост, телесная мера и нравственный плод",),
    6: ("пост, телесная мера и нравственный плод",),
    7: ("спорная атрибуция, покаяние и образ Раави",),
    8: ("покаяние, сокрушение и недопустимость отчаяния",),
    9: ("сомнительная атрибуция, Евхаристия, Суд и церковное собрание",),
}


CONFIGS = (
    ReviewConfig(
        "afanasij_voploshhenie",
        "АВ",
        "01_afanasij.md",
        1,
        9,
        "главы",
        AFANASIJ_RISKS,
    ),
    ReviewConfig(
        "makarij_duhovnye_besedy",
        "МБ",
        "02_makarij_001_025.md",
        1,
        25,
        "беседы",
        MAKARIJ_RISKS,
    ),
    ReviewConfig(
        "makarij_duhovnye_besedy",
        "МБ",
        "03_makarij_026_050.md",
        26,
        50,
        "беседы",
        MAKARIJ_RISKS,
    ),
    ReviewConfig(
        "ioann_zlatoust_pokajanie",
        "ИЗ",
        "04_zlatoust.md",
        1,
        9,
        "беседы",
        ZLATOUST_RISKS,
    ),
)


def tests_by_chapter(data: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    for chapter in data.get("chapters", []):
        number = int(chapter["number"])
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
                raise ValueError(f"Глава {number}, вопрос {index}: нет объяснения")
        result[number] = questions
    return result


def load_verified_book(
    root: Path,
    book_id: str,
) -> tuple[dict[str, Any], dict[int, list[dict[str, Any]]], Path, Path]:
    book_path = root / f"{book_id}.json"
    tests_path = root / "content_tests" / f"{book_id}.json"
    book = common.load_json(book_path)
    external = common.load_json(tests_path)
    if book.get("id") != book_id or external.get("book_id") != book_id:
        raise ValueError(f"{book_id}: неверный идентификатор")
    book_tests = tests_by_chapter(book)
    external_tests = tests_by_chapter(external)
    if book_tests != external_tests:
        raise ValueError(f"{book_id}: встроенные и редакционные тесты не совпадают")
    if len(book.get("chapters", [])) != book.get("chapters_count"):
        raise ValueError(f"{book_id}: chapters_count не совпадает")
    return book, book_tests, book_path, tests_path


def render_index(
    books: dict[str, dict[str, Any]],
    commit: str,
    hashes: dict[str, tuple[str, str]],
) -> str:
    rows = []
    for book_id in (
        "afanasij_voploshhenie",
        "makarij_duhovnye_besedy",
        "ioann_zlatoust_pokajanie",
    ):
        book = books[book_id]
        source_sha, tests_sha = hashes[book_id]
        rows.append(
            f"| {book['author']} · «{book['work']}» | {book['version']} | "
            f"{book['chapters_count']} | "
            f"`{source_sha}` | `{tests_sha}` |"
        )
    table = "\n".join(rows)
    return f"""<!-- early-fathers-review-packet: content={commit} -->
# Богословская рецензия тестов к трём книгам

Пакет фиксирует 68 глав и 204 вопроса из уже опубликованных книг. Генератор
подтвердил полное совпадение встроенных и редакционных тестов.

- Входной commit: `{commit}`

| Книга | Версия | Главы | SHA-256 книги | SHA-256 тестов |
|---|---:|---:|---|---|
{table}

## Файлы

- [01_afanasij.md](01_afanasij.md) — святитель Афанасий, главы 1–9.
- [02_makarij_001_025.md](02_makarij_001_025.md) — преподобный Макарий,
  беседы 1–25.
- [03_makarij_026_050.md](03_makarij_026_050.md) — преподобный Макарий,
  беседы 26–50.
- [04_zlatoust.md](04_zlatoust.md) — святитель Иоанн Златоуст, беседы 1–9.

## Обязательные оговорки

- Корпус духовных бесед публикуется под традиционным именем преподобного
  Макария Египетского.
- Седьмая беседа цикла о покаянии в современной атрибуции принадлежит
  епископу Севериану Габальскому.
- Атрибуция девятой беседы цикла о покаянии считается сомнительной.

## Что проверять

1. Соответствует ли ключ первоисточнику и православному вероучению.
2. Не говорит ли объяснение больше, чем позволяет текст.
3. Однозначно ли неверны дистракторы и остаются ли они правдоподобными.
4. Не превращён ли образный аскетический язык в буквальную догматическую
   формулу.
5. Не усиливает ли вопрос отчаяние, суеверие, страх или осуждение ближнего.
6. Учтены ли жанр, историческая полемика и атрибуционные оговорки.

## Как вернуть замечания

Замечания нужно вставлять прямо в тело сообщения:

```text
Версия: content {commit[:7]}
Проверенный блок: АВ001–АВ009 / МБ001–МБ025 / МБ026–МБ050 / ИЗ001–ИЗ009
ID: МБ015.2
Уровень: BLOCKER / MAJOR / MINOR / STYLE
Поле: вопрос / ответ A–C / объяснение
Проблема:
Предлагаемая правка:
Основание или источник:
Итог блока: проверен полностью; иных богословских замечаний нет.
```
"""


def render_packet(root: Path, commit: str) -> dict[str, str]:
    loaded: dict[
        str,
        tuple[dict[str, Any], dict[int, list[dict[str, Any]]], Path, Path],
    ] = {}
    for book_id in {config.book_id for config in CONFIGS}:
        loaded[book_id] = load_verified_book(root, book_id)

    books = {book_id: values[0] for book_id, values in loaded.items()}
    hashes = {
        book_id: (common.sha256(values[2]), common.sha256(values[3]))
        for book_id, values in loaded.items()
    }
    rendered = {
        "00_PACKET.md": render_index(books, commit, hashes),
    }
    for config in CONFIGS:
        book, tests, book_path, tests_path = loaded[config.book_id]
        chapters = [
            chapter
            for chapter in book["chapters"]
            if config.first <= int(chapter["number"]) <= config.last
        ]
        notes = {
            int(chapter["number"]): str(chapter["attribution_note"])
            for chapter in chapters
            if chapter.get("attribution_note")
        }
        content = common.render_chunk(
            book,
            chapters,
            tests,
            commit,
            common.sha256(book_path),
            common.sha256(tests_path),
            risk_tags=config.risk_tags,
            chapter_notes=notes,
        )
        content = (
            content.replace("ИД", config.prefix)
            .replace(" · главы ", f" · {config.unit_plural} ")
            .replace(
                "SHA-256 комплекта черновиков",
                "SHA-256 редакционного файла тестов",
            )
        )
        if config.unit_plural == "беседы":
            content = content.replace("Фрагмент главы", "Фрагмент беседы")
        editorial_note = str(book.get("editorial_note", "")).strip()
        if editorial_note:
            author_line = f"- Автор: {book['author']}"
            content = content.replace(
                author_line,
                f"{author_line}\n- Редакторская оговорка: {editorial_note}",
                1,
            )
        rendered[config.filename] = content
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--content-commit")
    args = parser.parse_args()
    root = args.root.resolve()
    commit = args.content_commit or common.git_head(root)
    rendered = render_packet(root, commit)
    common.write_packet(args.output_dir.resolve(), rendered)
    total_bytes = sum(len(value.encode("utf-8")) for value in rendered.values())
    print(
        f"Wrote {len(rendered)} files to {args.output_dir.resolve()} "
        f"({total_bytes} bytes)"
    )


if __name__ == "__main__":
    main()
