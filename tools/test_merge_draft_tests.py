import json
from pathlib import Path
import tempfile
import unittest

from tools import merge_draft_tests as merger


class MergeDraftTestsTest(unittest.TestCase):
    def make_root(self, root: Path) -> Path:
        drafts = root / "content_tests" / "drafts"
        drafts.mkdir(parents=True)
        book_path = root / "bundled_book.json"
        book_path.write_text(
            json.dumps(
                {
                    "id": "sample",
                    "chapters": [
                        {"number": 1},
                        {"number": 2},
                    ],
                }
            ),
            encoding="utf-8",
        )
        (drafts / "sample_01.json").write_text(
            json.dumps(
                {
                    "book_id": "sample",
                    "chapters": [
                        {
                            "number": 1,
                            "test": [
                                {"question": "Первый?"},
                                {"question": "Второй?"},
                                {"question": "Третий?"},
                            ],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return book_path

    def test_external_book_and_documented_exclusion_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book_path = self.make_root(root)
            output_path = merger.merge_drafts(
                root,
                "sample",
                book_path,
                {2: "Структурное примечание без самостоятельного урока"},
            )
            output = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(len(output["chapters"]), 1)
        self.assertEqual(
            output["excluded_chapters"],
            [
                {
                    "number": 2,
                    "reason": "Структурное примечание без самостоятельного урока",
                }
            ],
        )

    def test_unaccounted_chapter_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book_path = self.make_root(root)

            with self.assertRaisesRegex(ValueError, "пропущены=\\[2\\]"):
                merger.merge_drafts(root, "sample", book_path)


if __name__ == "__main__":
    unittest.main()
