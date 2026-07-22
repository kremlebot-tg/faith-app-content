import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.embed_book_tests import embed_book_tests, update_manifest


class EmbedBookTestsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "content_tests").mkdir()
        self.book = {
            "id": "sample",
            "version": 2,
            "chapters_count": 2,
            "chapters": [
                {
                    "number": 1,
                    "title": "Первая",
                    "paragraphs": ["Проверенный текст."],
                    "scripture_refs": [],
                },
                {
                    "number": 2,
                    "title": "Вторая",
                    "paragraphs": ["Ещё один текст."],
                    "scripture_refs": [],
                },
            ],
        }
        (self.root / "sample.json").write_text(
            json.dumps(self.book, ensure_ascii=False), encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_tests(self, chapters: list[dict]) -> None:
        path = self.root / "content_tests" / "sample.json"
        path.write_text(
            json.dumps({"book_id": "sample", "chapters": chapters}, ensure_ascii=False),
            encoding="utf-8",
        )

    def test_embeds_tests_and_preserves_every_other_field(self) -> None:
        tests = [{"question": "Что сказано?"}]
        self.write_tests([
            {"number": 1, "test": tests},
            {"number": 2, "test": tests},
        ])

        _, raw = embed_book_tests(self.root, "sample")
        updated = json.loads(raw)

        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["chapters"][0]["paragraphs"], ["Проверенный текст."])
        self.assertEqual(updated["chapters"][0]["test"], tests)

    def test_rejects_incomplete_chapter_coverage(self) -> None:
        self.write_tests([{"number": 1, "test": []}])

        with self.assertRaisesRegex(ValueError, r"пропущены=\[2\]"):
            embed_book_tests(self.root, "sample")

    def test_allows_documented_exclusion_and_removes_old_test(self) -> None:
        self.book["chapters"][1]["test"] = [{"question": "Устаревший вопрос?"}]
        (self.root / "sample.json").write_text(
            json.dumps(self.book, ensure_ascii=False), encoding="utf-8"
        )
        path = self.root / "content_tests" / "sample.json"
        path.write_text(
            json.dumps(
                {
                    "book_id": "sample",
                    "chapters": [{"number": 1, "test": []}],
                    "excluded_chapters": [
                        {"number": 2, "reason": "Редакторское приложение"}
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        _, raw = embed_book_tests(self.root, "sample")
        updated = json.loads(raw)

        self.assertNotIn("test", updated["chapters"][1])

    def test_rejects_exclusion_without_reason(self) -> None:
        path = self.root / "content_tests" / "sample.json"
        path.write_text(
            json.dumps(
                {
                    "book_id": "sample",
                    "chapters": [{"number": 1, "test": []}],
                    "excluded_chapters": [{"number": 2, "reason": ""}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "требует number и reason"):
            embed_book_tests(self.root, "sample")

    def test_updates_manifest_from_exact_release_bytes(self) -> None:
        self.write_tests([
            {"number": 1, "test": []},
            {"number": 2, "test": []},
        ])
        (self.root / "manifest.json").write_text(
            json.dumps({"last_updated": "old", "library": [{"id": "sample"}]}),
            encoding="utf-8",
        )
        output = embed_book_tests(self.root, "sample")

        update_manifest(self.root, [output], "v9.8.7", "2026-07-22")

        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        item = manifest["library"][0]
        self.assertEqual(manifest["last_updated"], "2026-07-22")
        self.assertEqual(item["size_bytes"], len(output[1]))
        self.assertEqual(item["sha256"], hashlib.sha256(output[1]).hexdigest())
        self.assertTrue(item["download_url"].endswith("/v9.8.7/sample.json"))


if __name__ == "__main__":
    unittest.main()
