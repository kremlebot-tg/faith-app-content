from pathlib import Path
import tempfile
import unittest

from tools import audit_review_coverage as review


class ReviewCoverageAuditTest(unittest.TestCase):
    def test_repository_has_complete_review_packet_coverage(self) -> None:
        result = review.audit(review.ROOT)

        self.assertEqual(len(result), 9)
        self.assertEqual(sum(value[0] for value in result.values()), 1161)
        self.assertEqual(sum(value[1] for value in result.values()), 1161)
        registry = review.render_registry(review.ROOT, "a" * 40)
        self.assertIn("681\nопубликованный вопрос", registry)
        self.assertIn("480 вопросов в черновиках", registry)
        self.assertEqual(registry.count("| ожидается |"), 9)

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


if __name__ == "__main__":
    unittest.main()
