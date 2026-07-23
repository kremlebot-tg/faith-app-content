import json
from pathlib import Path
import tempfile
import unittest

from tools import build_ignatius_review_packet as packet


class IgnatiusReviewPacketTest(unittest.TestCase):
    def test_repository_packet_has_complete_stable_ids(self) -> None:
        rendered = packet.render_packet(
            packet.ROOT / "ignatij_prinoshenie.json",
            packet.ROOT / "content_tests" / "drafts",
            "b" * 40,
        )

        self.assertEqual(
            set(rendered),
            {
                "00_PACKET.md",
                "01_chapters_001_015.md",
                "02_chapters_016_030.md",
                "03_chapters_031_045.md",
                "04_chapters_046_060.md",
            },
        )
        body = "\n".join(rendered.values())
        self.assertEqual(body.count("**Вердикт:**"), 180)
        self.assertIn("### ИП001.1", body)
        self.assertIn("### ИП060.3", body)
        self.assertIn("60 глав и 180", rendered["00_PACKET.md"])
        self.assertNotIn("> Ввeдение", rendered["01_chapters_001_015.md"])
        self.assertNotIn("> Введение", rendered["04_chapters_046_060.md"])
        self.assertIn(
            "отчаяние, самоповреждение и надежда",
            rendered["04_chapters_046_060.md"],
        )

    def test_rejects_incomplete_draft_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            drafts = Path(temporary)
            source = {
                "book_id": packet.BOOK_ID,
                "chapters": [],
            }
            (drafts / f"{packet.BOOK_ID}_01_05.json").write_text(
                json.dumps(source),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Неполное покрытие"):
                packet.common.load_drafts(
                    drafts,
                    packet.BOOK_ID,
                    set(range(1, packet.CHAPTER_COUNT + 1)),
                )


if __name__ == "__main__":
    unittest.main()
