import json
from pathlib import Path
import tempfile
import unittest

from tools import build_damaskin_review_packet as packet


class DamaskinReviewPacketTest(unittest.TestCase):
    def test_repository_packet_has_complete_stable_ids(self) -> None:
        rendered = packet.render_packet(
            packet.ROOT / "ioann_damaskin.json",
            packet.ROOT / "content_tests" / "drafts",
            "a" * 40,
        )

        self.assertEqual(
            set(rendered),
            {
                "00_README.md",
                "01_chapters_001_025.md",
                "02_chapters_026_050.md",
                "03_chapters_051_075.md",
                "04_chapters_076_100.md",
            },
        )
        body = "\n".join(rendered.values())
        self.assertEqual(body.count("**Вердикт:**"), 300)
        self.assertIn("### ИД001.1", body)
        self.assertIn("### ИД100.3", body)
        self.assertIn("100 глав и 300 вопросов", rendered["00_README.md"])

    def test_rejects_incomplete_draft_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            drafts = Path(temporary)
            source = {
                "book_id": "ioann_damaskin",
                "chapters": [],
            }
            (drafts / "ioann_damaskin_01_05.json").write_text(
                json.dumps(source),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Неполное покрытие"):
                packet.load_drafts(
                    drafts,
                    "ioann_damaskin",
                    set(range(1, 101)),
                )


if __name__ == "__main__":
    unittest.main()
