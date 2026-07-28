#!/usr/bin/env python3
"""Build a deterministic review packet for Cyril of Jerusalem."""

from __future__ import annotations

import argparse
from pathlib import Path

if __package__:
    from tools import build_damaskin_review_packet as common
else:
    import build_damaskin_review_packet as common


ROOT = Path(__file__).resolve().parents[1]
BOOK_ID = "kirill_ierusalimskij_oglasitelnye"
DEFAULT_OUTPUT = ROOT / "reviews" / "kirill_ierusalimskij"
RISK_TAGS = {
    1: ("оглашение, намерение и подготовка к Крещению",),
    2: ("покаяние, надежда и свобода человека",),
    3: ("происхождение зла и свобода воли",),
    4: ("Крещение водой и Святым Духом",),
    5: ("правило веры, Писание и воскресение тела",),
    6: ("вера как дар и свободный ответ человека",),
    7: ("единобожие и историческая антиеретическая полемика",),
    8: ("Божие отцовство и усыновление по благодати",),
    9: ("всемогущество, Промысл и Божие попущение",),
    10: ("творение, Промысл и исторические естественно-научные образы",),
    11: ("имена Христа и единство Его Лица",),
    12: ("вечное рождение Единородного Сына",),
    13: ("Воплощение, Богородица и историческая полемика",),
    14: ("Крест, искупление и историческая полемика",),
    15: ("Воскресение и Вознесение Христа",),
    16: ("Второе Пришествие и недопустимость вычисления сроков",),
    17: ("Святой Дух, единосущие и историческая полемика",),
    18: ("Пятидесятница и различение духовных даров",),
    19: ("воскресение тела, Суд и кафоличность Церкви",),
    20: ("отречение от сатаны и обращение ко Христу",),
    21: ("Крещение как участие в смерти и Воскресении Христа",),
    22: ("Миропомазание и действие Святого Духа",),
    23: ("Евхаристия и реальность Тела и Крови Христовых",),
    24: ("анафора, эпиклеза и приготовление к Причащению",),
}


def render_readme(
    book: dict,
    commit: str,
    source_sha: str,
    drafts_sha: str,
) -> str:
    return f"""<!-- cyril-review-packet: content={commit} -->
# Богословская рецензия тестов к книге «{book['work']}»

Пакет фиксирует полный корпус из 24 поучений и 72 вопросов: предварительное
поучение, восемнадцать огласительных и пять тайноводственных. Тесты прошли
автоматическую проверку формы и внутреннюю редактуру, но человеческая
богословская рецензия пока ожидается.

- Автор: {book['author']}
- Входной commit: `{commit}`
- SHA-256 книги: `{source_sha}`
- SHA-256 комплекта черновиков: `{drafts_sha}`
- Источник: [{book['source']}]({book['source']})

## Файлы

- [01_chapters_001_012.md](01_chapters_001_012.md) — поучения 1–12.
- [02_chapters_013_024.md](02_chapters_013_024.md) — поучения 13–24.

## Что проверять

1. Следует ли ключ точному смыслу поучения и православному вероучению.
2. Не превращена ли историческая антиеретическая полемика в современное
   обобщение о людях.
3. Не говорит ли объяснение больше, чем позволяет первоисточник.
4. Остаются ли дистракторы правдоподобными, но однозначно неверными.
5. Переданы ли Крещение, Миропомазание и Евхаристия без символического
   обесценивания и без магического понимания Таинств.

## Как вернуть замечания

Из-за ненадёжной передачи вложений замечания нужно вставлять прямо в тело
сообщения:

```text
Версия: content {commit[:7]}
Проверенный блок: КИ001–КИ012
ID: КИ023.2
Уровень: BLOCKER / MAJOR / MINOR / STYLE
Поле: вопрос / ответ A–C / объяснение
Проблема:
Предлагаемая правка:
Основание или источник:
Итог блока: проверен полностью; иных богословских замечаний нет.
```
"""


def render_packet(book_path: Path, drafts_dir: Path, commit: str) -> dict[str, str]:
    book = common.load_json(book_path)
    chapters = book.get("chapters", [])
    if book.get("id") != BOOK_ID:
        raise ValueError(f"Ожидается книга {BOOK_ID}")
    if book.get("chapters_count") != 24 or len(chapters) != 24:
        raise ValueError("Ожидаются 24 поучения")
    numbers = [int(chapter["number"]) for chapter in chapters]
    if numbers != list(range(1, 25)):
        raise ValueError("Ожидаются поучения 1–24 без пропусков")

    tests, draft_paths = common.load_drafts(
        drafts_dir, BOOK_ID, set(numbers)
    )
    source_sha = common.sha256(book_path)
    drafts_sha = common.combined_sha256(draft_paths)
    rendered = {
        "00_PACKET.md": render_readme(book, commit, source_sha, drafts_sha)
    }
    for index, start in enumerate((0, 12), start=1):
        chunk = chapters[start : start + 12]
        first = int(chunk[0]["number"])
        last = int(chunk[-1]["number"])
        filename = f"{index:02d}_chapters_{first:03d}_{last:03d}.md"
        text = common.render_chunk(
            book,
            chunk,
            tests,
            commit,
            source_sha,
            drafts_sha,
            risk_tags=RISK_TAGS,
        )
        rendered[filename] = text.replace("ИД", "КИ")
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
        args.book.resolve(), args.drafts_dir.resolve(), commit
    )
    common.write_packet(args.output_dir.resolve(), rendered)
    print(f"Wrote {len(rendered)} files to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
