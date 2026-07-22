#!/usr/bin/env python3
"""Детерминированный импорт выбранных PD-изданий с azbyka.ru.

Скрипт переносит только текст дореволюционных изданий, указанных в BOOKS.
Современные аннотации страницы и элементы интерфейса в книги не попадают.
Авторские тесты из ``content_tests/`` встраиваются в ``chapters[].test``.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any


USER_AGENT = "Mozilla/5.0 (Faith-App-PD-content-import)"
AZBYKA = "https://azbyka.ru"
TAIL_MARKERS = (
    "article-footer",
    "Вам может быть интересно",
    "related-header",
    "book-comments",
    "Telegram-каналы",
)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)
HEADING_RE = re.compile(
    r'<(h2|h3)[^>]*class="[^"]*text-center[^"]*"[^>]*>(.*?)</\1>',
    re.S | re.I,
)
PARAGRAPH_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
SCRIPTURE_RE = re.compile(
    r'<a[^>]+href="([^"]*?/biblia/\?[^"]+)"[^>]*>(.*?)</a>',
    re.S | re.I,
)
NOTE_REFERENCE_RE = re.compile(
    r'<a\b[^>]*href=["\']#((?:foot)?note\d+)["\']'
    r'[^>]*id=["\']\1_return["\'][^>]*>.*?</a>',
    re.S | re.I,
)
NOTE_BLOCK_RE = re.compile(
    r'<a\s+id=["\']((?:foot)?note\d+)["\']\s*></a>\s*'
    r'<div\s+class=["\']note["\'][^>]*>.*?<p\b[^>]*>(.*?)</p>\s*</div>',
    re.S | re.I,
)
TEXT_REPLACEMENTS = {
    'Неточно. Правильно «где ти смерте жало? где ти аде победа?"_':
        'Неточно. Правильно: «Где ти, смерте, жало? Где ти, аде, победа?»',
    'a=po tou Kuríou': 'ἀπὸ τοῦ Κυρίου («от Господа»)',
    'a=po tou a=rníou': 'ἀπὸ τοῦ ἀρνίου («от Агнца»)',
    'окончание беседы переведено по изд. Флосса.':
        'Окончание беседы переведено по изд. Флосса.',
}


BOOKS: dict[str, dict[str, Any]] = {
    "ioann_zlatoust_pokajanie": {
        "id": "ioann_zlatoust_pokajanie",
        "author": "Иоанн Златоуст",
        "work": "Беседы о покаянии",
        "century": "IV",
        "place": "Антиохия, вероятно",
        "chapter_label": "Беседа",
        "mode": "headings",
        "count": 9,
        "expected_notes": 14,
        "url": "https://azbyka.ru/otechnik/Ioann_Zlatoust/o_pokajanii/",
        "translator": "Перевод Санкт-Петербургской духовной академии",
        "source_edition": (
            "Творения святого отца нашего Иоанна Златоуста. Т. 2. "
            "Санкт-Петербург, 1896. С. 305–386."
        ),
        "editorial_note": (
            "Седьмая беседа в современной атрибуции принадлежит епископу "
            "Севериану Габальскому; атрибуция девятой беседы считается сомнительной. "
            "Местом произнесения цикла предположительно была Антиохия."
        ),
    },
    "afanasij_voploshhenie": {
        "id": "afanasij_voploshhenie",
        "author": "Афанасий Великий",
        "work": "Слово о воплощении Бога-Слова",
        "century": "IV",
        "place": "Александрия",
        "chapter_label": "Глава",
        "mode": "numbered_pages",
        "url": (
            "https://azbyka.ru/otechnik/Afanasij_Velikij/"
            "slovo-o-voploshhenii-boga-slova-i-o-prishestvii-ego-k-nam-vo-ploti"
        ),
        "count": 9,
        "expected_notes": 2,
        "title_strip": r"^Глава\s+\d+\.\s*",
        "translator": "Перевод ТСО, 1902 год",
        "source_edition": (
            "Творения иже во святых отца нашего Афанасия Великого. "
            "Ч. 1. Сергиев Посад, 1902. С. 191–263."
        ),
    },
    "makarij_duhovnye_besedy": {
        "id": "makarij_duhovnye_besedy",
        "author": "Макарий Великий",
        "work": "Духовные беседы",
        "century": "IV",
        "place": "Египет",
        "chapter_label": "Беседа",
        "mode": "headings",
        "count": 50,
        "expected_notes": 6,
        "url": "https://azbyka.ru/otechnik/Makarij_Velikij/duhovnye-besedy-1-50/",
        "title_strip": r"^Беседа\s+\d+\.\s*",
        "translator": "Русский перевод издания 1880 года",
        "source_edition": (
            "Преподобного отца нашего Макария Египетского духовные беседы, "
            "послание и слова. 3-е изд. Москва, 1880. С. 1–415."
        ),
        "editorial_note": (
            "Корпус духовных бесед публикуется под традиционным именем "
            "преподобного Макария Египетского."
        ),
    },
}


def fetch(url: str) -> str:
    last_error = ""
    for attempt in range(3):
        result = subprocess.run(
            [
                "curl", "-fsSL", "--max-time", "40", "--retry", "2",
                "-A", USER_AGENT, url,
            ],
            capture_output=True,
            timeout=50,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.decode("utf-8", "ignore")
        last_error = result.stderr.decode("utf-8", "ignore").strip()
        time.sleep(attempt + 1)
    raise RuntimeError(f"Не удалось загрузить {url}: {last_error}")


def clean_text(fragment: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value).replace("\xa0", " ")
    value = re.sub(r"[ \t\r\n]+", " ", value).strip()
    for source, replacement in TEXT_REPLACEMENTS.items():
        value = value.replace(source, replacement)
    return value


def note_references(fragment: str) -> list[str]:
    return NOTE_REFERENCE_RE.findall(fragment)


def clean_content_text(fragment: str) -> str:
    """Убирает экранные номера сносок, сохраняя сам текст абзаца."""
    return clean_text(NOTE_REFERENCE_RE.sub("", fragment))


def extract_notes(body: str) -> dict[str, str]:
    notes: dict[str, str] = {}
    for match in NOTE_BLOCK_RE.finditer(body):
        note_id = match.group(1)
        if note_id in notes:
            raise ValueError(f"Повторный идентификатор примечания: {note_id}")
        text = clean_text(match.group(2))
        if not text:
            raise ValueError(f"Пустое примечание: {note_id}")
        notes[note_id] = text
    return notes


def content_region(page: str) -> tuple[str, str]:
    h1 = H1_RE.search(page)
    title = clean_text(h1.group(1)) if h1 else ""
    start = h1.end() if h1 else 0
    end = len(page)
    for marker in TAIL_MARKERS:
        position = page.find(marker, start)
        if position >= 0:
            end = min(end, position)
    return title, page[start:end]


def scripture_refs(fragment: str) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in SCRIPTURE_RE.finditer(fragment):
        href = match.group(1)
        url = href if href.startswith("http") else AZBYKA + href
        text = clean_text(match.group(2))
        key = (text, url)
        if text and key not in seen:
            seen.add(key)
            refs.append({"text": text, "url": url})
    return refs


def ordered_elements(
    page: str,
) -> tuple[str, list[dict[str, Any]], dict[str, str]]:
    title, body = content_region(page)
    events: list[tuple[int, dict[str, Any]]] = []
    for match in HEADING_RE.finditer(body):
        events.append((match.start(), {
            "kind": "heading",
            "text": clean_content_text(match.group(2)),
            "refs": [],
            "note_refs": note_references(match.group(2)),
        }))
    for match in PARAGRAPH_RE.finditer(body):
        text = clean_content_text(match.group(1))
        if text and len(text) >= 2:
            events.append((match.start(), {
                "kind": "paragraph",
                "text": text,
                "refs": scripture_refs(match.group(0)),
                "note_refs": note_references(match.group(0)),
            }))
    events.sort(key=lambda item: item[0])
    return title, [event for _, event in events], extract_notes(body)


def strip_note_section(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for index in range(len(elements) - 1):
        if (
            elements[index]["kind"] == "paragraph"
            and elements[index]["text"] == "* * *"
            and elements[index + 1]["kind"] == "paragraph"
            and elements[index + 1]["text"] == "Примечания"
        ):
            return elements[:index]
    return elements


def resolve_notes(
    note_ids: list[str],
    note_texts: dict[str, str],
    context: str,
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for note_id in note_ids:
        if note_id in seen:
            continue
        if note_id not in note_texts:
            raise ValueError(f"{context}: нет текста примечания {note_id}")
        seen.add(note_id)
        result.append(note_texts[note_id])
    return result


def deduplicate_refs(refs: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        key = (ref["text"], ref["url"])
        if key not in seen:
            seen.add(key)
            result.append(ref)
    return result


def build_heading_chapters(config: dict[str, Any]) -> list[dict[str, Any]]:
    _, raw_elements, note_texts = ordered_elements(fetch(config["url"]))
    elements = strip_note_section(raw_elements)
    chapters: list[dict[str, Any]] = []
    current_title: str | None = None
    paragraphs: list[str] = []
    refs: list[dict[str, str]] = []
    note_ids: list[str] = []
    used_note_ids: set[str] = set()

    def flush() -> None:
        nonlocal paragraphs, refs, note_ids
        if current_title is None:
            return
        title = current_title
        if config.get("title_strip"):
            title = re.sub(config["title_strip"], "", title).strip()
        chapter: dict[str, Any] = {
            "number": len(chapters) + 1,
            "title": title,
            "paragraphs": paragraphs,
            "scripture_refs": deduplicate_refs(refs),
        }
        notes = resolve_notes(note_ids, note_texts, config["id"])
        if notes:
            chapter["notes"] = notes
            used_note_ids.update(note_ids)
        chapters.append(chapter)
        paragraphs = []
        refs = []
        note_ids = []

    for element in elements:
        if element["kind"] == "heading":
            flush()
            current_title = element["text"]
            note_ids.extend(element["note_refs"])
        elif current_title is not None:
            paragraphs.append(element["text"])
            refs.extend(element["refs"])
            note_ids.extend(element["note_refs"])
    flush()
    if set(note_texts) != used_note_ids:
        missing = sorted(set(note_texts) - used_note_ids)
        raise ValueError(f'{config["id"]}: непривязанные примечания {missing}')
    if len(note_texts) != config.get("expected_notes", len(note_texts)):
        raise ValueError(
            f'{config["id"]}: ожидалось примечаний {config["expected_notes"]}, '
            f'получено {len(note_texts)}'
        )
    return chapters


def build_numbered_page_chapters(config: dict[str, Any]) -> list[dict[str, Any]]:
    chapters: list[dict[str, Any]] = []
    note_count = 0
    for number in range(1, config["count"] + 1):
        page_title, raw_elements, note_texts = ordered_elements(
            fetch(f'{config["url"]}/{number}')
        )
        elements = strip_note_section(raw_elements)
        title = re.sub(config.get("title_strip", ""), "", page_title).strip()
        paragraphs = [
            element["text"] for element in elements
            if element["kind"] == "paragraph"
        ]
        refs = deduplicate_refs([
            ref for element in elements for ref in element["refs"]
        ])
        note_ids = [
            note_id for element in elements for note_id in element["note_refs"]
        ]
        notes = resolve_notes(note_ids, note_texts, f'{config["id"]}:{number}')
        if set(note_ids) != set(note_texts):
            missing = sorted(set(note_texts) - set(note_ids))
            raise ValueError(
                f'{config["id"]}:{number}: непривязанные примечания {missing}'
            )
        note_count += len(notes)
        chapter: dict[str, Any] = {
            "number": number,
            "title": title,
            "paragraphs": paragraphs,
            "scripture_refs": refs,
        }
        if notes:
            chapter["notes"] = notes
        chapters.append(chapter)
        time.sleep(0.25)
    if note_count != config.get("expected_notes", note_count):
        raise ValueError(
            f'{config["id"]}: ожидалось примечаний {config["expected_notes"]}, '
            f'получено {note_count}'
        )
    return chapters


def attach_authored_tests(book_id: str, chapters: list[dict[str, Any]]) -> None:
    source = Path(__file__).resolve().parent.parent / "content_tests" / f"{book_id}.json"
    if not source.exists():
        return
    data = json.loads(source.read_text(encoding="utf-8"))
    assert data["book_id"] == book_id
    by_number = {chapter["number"]: chapter["test"] for chapter in data["chapters"]}
    available = {chapter["number"] for chapter in chapters}
    assert set(by_number).issubset(available)
    for chapter in chapters:
        if chapter["number"] in by_number:
            chapter["test"] = by_number[chapter["number"]]


def validate_book(book: dict[str, Any]) -> None:
    chapters = book["chapters"]
    assert book["chapters_count"] == len(chapters)
    assert [chapter["number"] for chapter in chapters] == list(range(1, len(chapters) + 1))
    assert all(chapter["title"].strip() for chapter in chapters)
    assert all(chapter["paragraphs"] for chapter in chapters)
    forbidden = {"Telegram-каналы", "Читать полностью", "Источник:"}
    for chapter in chapters:
        assert "*" not in chapter["title"]
        for text in chapter["paragraphs"] + chapter.get("notes", []):
            assert text not in forbidden
            assert "<" not in text and ">" not in text


def update_manifest(output_dir: Path, outputs: list[Path]) -> None:
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"Не найден манифест: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in manifest["library"]}
    for output in outputs:
        raw = output.read_bytes()
        book = json.loads(raw)
        if book["id"] not in by_id:
            raise ValueError(f'Книга {book["id"]} не зарегистрирована в манифесте')
        item = by_id[book["id"]]
        item["chapters_count"] = len(book["chapters"])
        item["size_bytes"] = len(raw)
        item["sha256"] = hashlib.sha256(raw).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_book(config: dict[str, Any], output_dir: Path) -> Path:
    if config["mode"] == "headings":
        chapters = build_heading_chapters(config)
    else:
        chapters = build_numbered_page_chapters(config)

    if len(chapters) != config["count"]:
        raise ValueError(
            f'{config["id"]}: ожидалось глав {config["count"]}, '
            f'получено {len(chapters)}'
        )

    output = output_dir / f'{config["id"]}.json'
    attach_authored_tests(config["id"], chapters)
    book = {
        "id": config["id"],
        "schema_version": 1,
        "version": 1,
        "author": config["author"],
        "work": config["work"],
        "century": config["century"],
        "place": config["place"],
        "translator": config["translator"],
        "source": config["url"],
        "source_edition": config["source_edition"],
        "license": "public domain",
        "chapter_label": config["chapter_label"],
        "chapters_count": len(chapters),
        "chapters": chapters,
    }
    if config.get("editorial_note"):
        book["editorial_note"] = config["editorial_note"]
    if config["id"] == "ioann_zlatoust_pokajanie":
        chapters[6]["attribution_note"] = (
            "По примечанию электронной редакции источника беседа принадлежит "
            "епископу Севериану Габальскому."
        )
        chapters[8]["attribution_note"] = (
            "Атрибуция этой беседы святителю Иоанну Златоусту считается сомнительной."
        )

    validate_book(book)
    raw = json.dumps(book, ensure_ascii=False, indent=2)
    output.write_text(raw, encoding="utf-8")
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    print(
        f'{config["id"]}: глав={len(chapters)}, байт={len(raw.encode("utf-8"))}, '
        f'sha256={digest}'
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", choices=["all", *BOOKS], default="all")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
    )
    parser.add_argument(
        "--update-manifest",
        action="store_true",
        help="обновить chapters_count, size_bytes и sha256 существующих записей",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    selected = BOOKS.values() if args.book == "all" else [BOOKS[args.book]]
    outputs = [build_book(config, args.output_dir) for config in selected]
    if args.update_manifest:
        update_manifest(args.output_dir, outputs)


if __name__ == "__main__":
    main()
