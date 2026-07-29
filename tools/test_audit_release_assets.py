from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from audit_release_assets import (
    LATEST_MANIFEST_URL,
    audit_release_assets,
)


def encoded(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")


class AuditReleaseAssetsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.book = {
            "id": "book",
            "author": "Автор",
            "work": "Книга",
            "chapters": [
                {
                    "number": 1,
                    "title": "Глава",
                    "paragraphs": ["Текст"],
                }
            ],
        }
        self.book_raw = encoded(self.book)
        self.url = (
            "https://example.test/releases/download/v1.0.0/book.json"
        )
        self.manifest = {
            "schema_version": 1,
            "last_updated": "2026-07-29",
            "library": [
                {
                    "id": "book",
                    "chapters_count": 1,
                    "size_bytes": len(self.book_raw),
                    "bundled": False,
                    "download_url": self.url,
                    "sha256": hashlib.sha256(self.book_raw).hexdigest(),
                },
                {
                    "id": "bundled",
                    "chapters_count": 1,
                    "bundled": True,
                },
            ],
        }
        (self.root / "book.json").write_bytes(self.book_raw)
        (self.root / "manifest.json").write_bytes(encoded(self.manifest))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_accepts_exact_release_and_latest_manifest(self) -> None:
        payloads = {
            self.url: self.book_raw,
            LATEST_MANIFEST_URL: encoded(self.manifest),
        }
        errors, stats = audit_release_assets(
            self.root,
            lambda url: payloads[url],
        )
        self.assertEqual(errors, [])
        self.assertEqual(stats["books"], 2)
        self.assertEqual(stats["remote_books"], 1)
        self.assertEqual(stats["verified_bytes"], len(self.book_raw))

    def test_rejects_changed_release_and_stale_latest_manifest(self) -> None:
        changed = encoded({**self.book, "work": "Подменённая книга"})
        stale_manifest = {**self.manifest, "last_updated": "2026-07-28"}
        payloads = {
            self.url: changed,
            LATEST_MANIFEST_URL: encoded(stale_manifest),
        }
        errors, _ = audit_release_assets(
            self.root,
            lambda url: payloads[url],
        )
        self.assertTrue(any("размер релиза" in error for error in errors))
        self.assertTrue(any("SHA-256" in error for error in errors))
        self.assertTrue(any("отличается от JSON" in error for error in errors))
        self.assertTrue(any("latest manifest" in error for error in errors))

    def test_reports_network_failure_without_crashing(self) -> None:
        def failed_fetch(url: str) -> bytes:
            raise RuntimeError(f"нет сети: {url}")

        errors, stats = audit_release_assets(self.root, failed_fetch)
        self.assertEqual(stats["remote_books"], 1)
        self.assertEqual(len(errors), 2)
        self.assertTrue(all("нет сети" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
