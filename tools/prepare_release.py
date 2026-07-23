#!/usr/bin/env python3
"""Prepare a deterministic, validated Faith App content release."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


RELEASE_TAG = "v1.0.2"
RELEASE_DATE = "2026-07-22"
BASE_URL = (
    "https://github.com/kremlebot-tg/faith-app-content/releases/download/"
    f"{RELEASE_TAG}"
)
SOURCE_DIGESTS = {
    "feofan_dukhovnaja_zhizn.json":
        "92716541d4fcae885e2f1f7ece61d8ff2edf3bfc7d2d855f627d5658b8e482c2",
    "ioann_lestvichnik.json":
        "09254329c6db738079ba6e947eb0f4b466204f49fdc1a7fcce5c96d35b6a5adf",
    "ignatij_prinoshenie.json":
        "93a5bf1fc8d7d160b76d60255c7eedca13e759dfd4fe7c550db3204299644030",
    "ioann_damaskin.json":
        "5140921811f591d7833eb80ffa3281c0b4693301c84b53631ef5225d2a4221bd",
}
EXPECTED_NOTE_CHAPTERS = {
    "feofan_dukhovnaja_zhizn.json": 11,
    "ioann_lestvichnik.json": 21,
    "ignatij_prinoshenie.json": 2,
    "ioann_damaskin.json": 0,
}


def canonical_bytes(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def split_note_tail(paragraphs: list[str]) -> tuple[list[str], list[str]]:
    cleaned = list(paragraphs)
    if cleaned and cleaned[-1] == "Telegram-каналы":
        cleaned.pop()
    for index in range(len(cleaned) - 2, -1, -1):
        if cleaned[index:index + 2] == ["* * *", "Примечания"]:
            return cleaned[:index], cleaned[index + 2:]
    return cleaned, []


def clean_book(path: Path) -> dict:
    raw = path.read_bytes()
    expected = SOURCE_DIGESTS[path.name]
    if digest(raw) != expected:
        raise ValueError(f"Unexpected source digest: {path.name}")

    book = json.loads(raw)
    note_chapters = 0
    for chapter in book["chapters"]:
        paragraphs, notes = split_note_tail(chapter["paragraphs"])
        chapter["paragraphs"] = paragraphs
        if notes:
            chapter["notes"] = notes
            note_chapters += 1
        if any(text == "Telegram-каналы" for text in paragraphs):
            raise ValueError(f"Non-tail Telegram marker: {path.name}, chapter {chapter['number']}")

    if path.name == "ioann_damaskin.json":
        replacements = 0
        for chapter in book["chapters"]:
            updated = []
            for paragraph in chapter["paragraphs"]:
                replacements += paragraph.count("вопло-1ился")
                updated.append(paragraph.replace("вопло-1ился", "воплотился"))
            chapter["paragraphs"] = updated
        if replacements != 1:
            raise ValueError(f"Expected one Damascene OCR repair, got {replacements}")

    if note_chapters != EXPECTED_NOTE_CHAPTERS[path.name]:
        raise ValueError(
            f"Unexpected note-tail count in {path.name}: {note_chapters}"
        )
    book["version"] = 2
    validate_book(book, path.name)
    return book


def validate_book(book: dict, name: str) -> None:
    chapters = book["chapters"]
    if book["chapters_count"] != len(chapters):
        raise ValueError(f"Chapter count mismatch: {name}")
    if [chapter["number"] for chapter in chapters] != list(range(1, len(chapters) + 1)):
        raise ValueError(f"Non-contiguous chapter numbers: {name}")

    forbidden = ("Telegram-каналы", "t.me/", "* * *")
    for chapter in chapters:
        kind = chapter.get("kind", "chapter")
        if kind == "section":
            if (chapter["paragraphs"] or chapter.get("scripture_refs") or
                    chapter.get("notes") or chapter.get("test") or
                    chapter.get("attribution_note") is not None):
                raise ValueError(
                    f"Structural section contains content in {name}, "
                    f"chapter {chapter['number']}"
                )
        elif kind != "chapter":
            raise ValueError(
                f"Unknown chapter kind in {name}, chapter {chapter['number']}: {kind}"
            )
        elif (not chapter["paragraphs"] or
                any(not str(value).strip() for value in chapter["paragraphs"])):
            raise ValueError(
                f"Empty readable chapter in {name}, chapter {chapter['number']}"
            )
        for paragraph in chapter["paragraphs"]:
            if any(marker in paragraph for marker in forbidden):
                raise ValueError(
                    f"Forbidden main-text marker in {name}, chapter {chapter['number']}"
                )
        if "вопло-1ился" in " ".join(chapter["paragraphs"]):
            raise ValueError(f"Known OCR corruption remains in {name}")


def update_manifest(root: Path, outputs: dict[str, bytes]) -> None:
    path = root / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["last_updated"] = RELEASE_DATE
    by_id = {item["id"]: item for item in manifest["library"]}
    by_id["avva_dorofey"]["chapters_count"] = 22

    for name, raw in outputs.items():
        book = json.loads(raw)
        item = by_id[book["id"]]
        item["chapters_count"] = len(book["chapters"])
        item["size_bytes"] = len(raw)
        item["download_url"] = f"{BASE_URL}/{name}"
        item["sha256"] = digest(raw)

    path.write_bytes(canonical_bytes(manifest))


def validate_manifest(root: Path) -> None:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest["library"]:
        name = f"{item['id']}.json"
        path = root / name
        if item.get("bundled"):
            continue
        if not path.exists():
            raise ValueError(f"Missing remote book in repository: {name}")
        raw = path.read_bytes()
        book = json.loads(raw)
        validate_book(book, name)
        if item["chapters_count"] != len(book["chapters"]):
            raise ValueError(f"Manifest chapter mismatch: {name}")
        sections = [
            chapter["number"] for chapter in book["chapters"]
            if chapter.get("kind") == "section"
        ]
        if item.get("section_numbers", []) != sections:
            raise ValueError(f"Manifest section mismatch: {name}")
        if item.get("size_bytes") != len(raw):
            raise ValueError(f"Manifest size mismatch: {name}")
        if item.get("sha256") != digest(raw):
            raise ValueError(f"Manifest digest mismatch: {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]

    if args.validate_only:
        validate_manifest(root)
        print("manifest.json and remote books: OK")
        return
    if args.source_dir is None:
        parser.error("--source-dir is required unless --validate-only is used")

    outputs = {}
    for name in SOURCE_DIGESTS:
        book = clean_book(args.source_dir / name)
        raw = canonical_bytes(book)
        (root / name).write_bytes(raw)
        outputs[name] = raw
        print(f"{name}: {len(raw)} bytes, sha256={digest(raw)}")

    update_manifest(root, outputs)
    validate_manifest(root)
    print("manifest.json: OK")


if __name__ == "__main__":
    main()
