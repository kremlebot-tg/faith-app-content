#!/usr/bin/env python3
"""Проверить живые GitHub Release-файлы библиотеки Faith App."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
LATEST_MANIFEST_URL = (
    "https://github.com/kremlebot-tg/faith-app-content/"
    "releases/latest/download/manifest.json"
)
Fetcher = Callable[[str], bytes]


def load_json(raw: bytes, location: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{location}: неверный UTF-8 JSON: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{location}: ожидается JSON-объект")
    return value


def network_fetch(url: str, *, timeout: float, attempts: int) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(
                url,
                headers={"User-Agent": "FaithAppReleaseAudit/1.0"},
            )
            with urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise ValueError(f"HTTP {response.status}")
                return response.read()
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(min(attempt, 3))
    raise RuntimeError(f"загрузка не удалась: {last_error}")


def audit_release_assets(
    root: Path,
    fetch: Fetcher,
) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    manifest_path = root / "manifest.json"
    local_manifest_raw = manifest_path.read_bytes()
    manifest = load_json(local_manifest_raw, str(manifest_path))
    library = manifest.get("library")
    if not isinstance(library, list):
        return ["manifest.json: отсутствует массив library"], {
            "books": 0,
            "remote_books": 0,
            "verified_bytes": 0,
        }

    remote_books = 0
    verified_bytes = 0
    for raw_entry in library:
        if not isinstance(raw_entry, dict):
            errors.append("manifest.json: запись книги не является объектом")
            continue
        book_id = str(raw_entry.get("id", "")).strip()
        if raw_entry.get("bundled"):
            continue
        remote_books += 1
        url = raw_entry.get("download_url")
        if not isinstance(url, str) or not url.startswith("https://"):
            errors.append(f"{book_id}: отсутствует HTTPS download_url")
            continue
        try:
            remote_raw = fetch(url)
        except Exception as error:
            errors.append(f"{book_id}: {error}")
            continue

        verified_bytes += len(remote_raw)
        expected_size = raw_entry.get("size_bytes")
        if len(remote_raw) != expected_size:
            errors.append(
                f"{book_id}: размер релиза {len(remote_raw)}, "
                f"в манифесте {expected_size}"
            )
        actual_digest = hashlib.sha256(remote_raw).hexdigest()
        if actual_digest != raw_entry.get("sha256"):
            errors.append(f"{book_id}: SHA-256 релиза не совпадает")

        local_path = root / f"{book_id}.json"
        if not local_path.is_file():
            errors.append(f"{book_id}: локальный опубликованный JSON не найден")
        elif remote_raw != local_path.read_bytes():
            errors.append(f"{book_id}: релиз отличается от JSON в main")

        try:
            remote_book = load_json(remote_raw, book_id)
        except ValueError as error:
            errors.append(str(error))
            continue
        chapters = remote_book.get("chapters")
        if remote_book.get("id") != book_id:
            errors.append(f"{book_id}: неверный id внутри релизного JSON")
        if not isinstance(chapters, list):
            errors.append(f"{book_id}: отсутствует массив chapters")
        elif len(chapters) != raw_entry.get("chapters_count"):
            errors.append(
                f"{book_id}: в релизе {len(chapters)} глав, "
                f"в манифесте {raw_entry.get('chapters_count')}"
            )

    try:
        latest_manifest_raw = fetch(LATEST_MANIFEST_URL)
    except Exception as error:
        errors.append(f"latest manifest: {error}")
    else:
        try:
            latest_manifest = load_json(
                latest_manifest_raw,
                "latest manifest",
            )
        except ValueError as error:
            errors.append(str(error))
        else:
            if latest_manifest != manifest:
                errors.append(
                    "latest manifest отличается от manifest.json в main"
                )

    return errors, {
        "books": len(library),
        "remote_books": remote_books,
        "verified_bytes": verified_bytes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args()
    if args.timeout <= 0 or args.attempts <= 0:
        parser.error("--timeout и --attempts должны быть положительными")

    def fetch(url: str) -> bytes:
        return network_fetch(
            url,
            timeout=args.timeout,
            attempts=args.attempts,
        )

    errors, stats = audit_release_assets(ROOT, fetch)
    print(
        f"books={stats['books']} remote_books={stats['remote_books']} "
        f"verified_bytes={stats['verified_bytes']} errors={len(errors)}"
    )
    for error in errors:
        print(f"ERROR {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
