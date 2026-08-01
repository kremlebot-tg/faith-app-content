import hashlib
from pathlib import Path
import tempfile
import unittest

from tools import audit_review_coverage as review


class ReviewCoverageAuditTest(unittest.TestCase):
    def test_repository_has_complete_review_packet_coverage(self) -> None:
        result = review.audit(review.ROOT)

        self.assertEqual(len(result), 15)
        self.assertEqual(sum(value[0] for value in result.values()), 1500)
        self.assertEqual(sum(value[1] for value in result.values()), 1500)
        registry = review.render_registry(review.ROOT, "a" * 40)
        self.assertIn("1500\nопубликованный вопрос", registry)
        self.assertIn("0 вопросов в черновиках", registry)
        self.assertEqual(registry.count("| ожидается |"), 15)

    def test_detects_packet_with_missing_verdict(self) -> None:
        entry = review.COVERAGE[0]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = review.ROOT / entry.files[0]
            target = root / entry.files[0]
            target.parent.mkdir(parents=True)
            text = source.read_text(encoding="utf-8")
            target.write_text(
                text.replace(review.VERDICT_MARKER, "", 1),
                encoding="utf-8",
            )
            altered = review.ReviewCoverage(
                entry.book_id,
                entry.prefix,
                entry.test_status,
                entry.expected_questions,
                entry.files,
            )
            verdicts, ids = review.packet_stats(root, altered)
            self.assertEqual(verdicts, entry.expected_questions - 1)
            self.assertEqual(len(ids), entry.expected_questions)

    def test_detects_stale_draft_packet_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            drafts = root / "content_tests" / "drafts"
            drafts.mkdir(parents=True)
            draft = drafts / "sample_01.json"
            draft.write_text('{"book_id":"sample"}\n', encoding="utf-8")
            metadata = root / "reviews" / "sample" / "00_PACKET.md"
            metadata.parent.mkdir(parents=True)
            metadata.write_text(
                "- SHA-256 комплекта черновиков: `" + "0" * 64 + "`\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "пакет рецензии устарел"):
                review.validate_draft_packet_digest(
                    root,
                    "sample",
                    "reviews/sample/00_PACKET.md",
                )

            digest = hashlib.sha256()
            digest.update(draft.name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(draft.read_bytes())
            digest.update(b"\0")
            metadata.write_text(
                f"- SHA-256 комплекта черновиков: `{digest.hexdigest()}`\n",
                encoding="utf-8",
            )
            review.validate_draft_packet_digest(
                root,
                "sample",
                "reviews/sample/00_PACKET.md",
            )

    def test_combined_content_tests_are_a_standalone_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tests = root / "content_tests"
            tests.mkdir()
            (tests / "sample.json").write_text(
                """
                {
                  "book_id": "sample",
                  "chapters": [
                    {"number": 1, "test": [{}, {}, {}]},
                    {"number": 2, "test": [{}, {}, {}]}
                  ]
                }
                """,
                encoding="utf-8",
            )
            entry = review.ReviewCoverage(
                "sample",
                "С",
                "опубликованы",
                6,
                (),
            )

            self.assertEqual(review.count_source_questions(root, entry), 6)


if __name__ == "__main__":
    unittest.main()
