#!/usr/bin/env python3
"""Embed authored chapter tests without changing verified book text."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any


RELEASE_BASE = "https://github.com/kremlebot-tg/faith-app-content/releases/download"


def canonical_bytes(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def without_tests(book: dict[str, Any]) -> dict[str, Any]:
    preserved = deepcopy(book)
    for chapter in preserved["chapters"]:
        chapter.pop("test", None)
    return preserved


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def authored_tests(root: Path, book: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    book_id = book["id"]
    path = root / "content_tests" / f"{book_id}.json"
    if not path.exists():
        raise ValueError(f"Не найден файл авторских тестов: {path}")
    source = load_json(path)
    if source.get("book_id") != book_id:
        raise ValueError(f"Неверный book_id в {path.name}")

    by_number: dict[int, list[dict[str, Any]]] = {}
    for chapter in source.get("chapters", []):
        number = chapter.get("number")
        if not isinstance(number, int):
            raise ValueError(f"Некорректный номер главы в {path.name}: {number!r}")
        if number in by_number:
            raise ValueError(f"Глава {number} повторяется в {path.name}")
        by_number[number] = chapter.get("test", [])

    book_numbers = {chapter["number"] for chapter in book["chapters"]}
    if set(by_number) != book_numbers:
        missing = sorted(book_numbers - set(by_number))
        extra = sorted(set(by_number) - book_numbers)
        raise ValueError(
            f"Неполное покрытие {book_id}: пропущены={missing}, лишние={extra}"
        )
    return by_number


def embed_book_tests(root: Path, book_id: str) -> tuple[Path, bytes]:
    path = root / f"{book_id}.json"
    if not path.exists():
        raise ValueError(f"Не найден файл книги: {path}")
    book = load_json(path)
    if book.get("id") != book_id:
        raise ValueError(f"Неверный id в {path.name}")
    if book.get("chapters_count") != len(book.get("chapters", [])):
        raise ValueError(f"Некорректное число глав в {path.name}")

    preserved = without_tests(book)
    tests = authored_tests(root, book)
    for chapter in book["chapters"]:
        chapter["test"] = tests[chapter["number"]]
    if without_tests(book) != preserved:
        raise AssertionError(f"Изменился основной текст книги {book_id}")

    raw = canonical_bytes(book)
    path.write_bytes(raw)
    return path, raw


def update_manifest(
    root: Path,
    outputs: list[tuple[Path, bytes]],
    release_tag: str,
    release_date: str | None,
) -> None:
    manifest_path = root / "manifest.json"
    manifest = load_json(manifest_path)
    by_id = {item["id"]: item for item in manifest["library"]}
    if release_date is not None:
        manifest["last_updated"] = release_date

    for path, raw in outputs:
        book = json.loads(raw)
        book_id = book["id"]
        if book_id not in by_id:
            raise ValueError(f"Книга {book_id} отсутствует в manifest.json")
        item = by_id[book_id]
        item["chapters_count"] = len(book["chapters"])
        item["size_bytes"] = len(raw)
        item["download_url"] = f"{RELEASE_BASE}/{release_tag}/{path.name}"
        item["sha256"] = hashlib.sha256(raw).hexdigest()

    manifest_path.write_bytes(canonical_bytes(manifest))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", action="append", required=True)
    parser.add_argument("--release-tag")
    parser.add_argument("--release-date")
    parser.add_argument("--update-manifest", action="store_true")
    args = parser.parse_args()
    if args.update_manifest and not args.release_tag:
        parser.error("--release-tag обязателен вместе с --update-manifest")

    root = Path(__file__).resolve().parents[1]
    outputs = [embed_book_tests(root, book_id) for book_id in args.book]
    if args.update_manifest:
        update_manifest(root, outputs, args.release_tag, args.release_date)
    for path, raw in outputs:
        print(
            f"{path.name}: {len(raw)} bytes, "
            f"sha256={hashlib.sha256(raw).hexdigest()}"
        )


if __name__ == "__main__":
    main()
