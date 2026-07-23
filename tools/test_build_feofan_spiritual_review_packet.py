import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools import build_feofan_spiritual_review_packet as packet


class FeofanSpiritualReviewPacketTest(unittest.TestCase):
    def test_repository_packet_has_complete_stable_ids(self) -> None:
        rendered = packet.render_packet(
            packet.ROOT / "feofan_dukhovnaja_zhizn.json",
            packet.ROOT / "content_tests" / "feofan_dukhovnaja_zhizn.json",
            packet.ROOT / "content_tests" / "drafts",
            "c" * 40,
        )

        self.assertEqual(
            set(rendered),
            {
                "00_PACKET.md",
                "01_letters_001_020.md",
                "02_letters_021_040.md",
                "03_letters_041_060.md",
                "04_letters_061_080.md",
            },
        )
        body = "\n".join(rendered.values())
        self.assertEqual(body.count("**Вердикт:**"), 240)
        self.assertEqual(body.count("**Итог ФД"), 80)
        self.assertIn("### ФД001.1", body)
        self.assertIn("### ФД080.3", body)
        self.assertIn("80 писем и\n240 вопросов", rendered["00_PACKET.md"])
        self.assertIn(
            "устаревшие научные аргументы",
            rendered["04_letters_061_080.md"],
        )

    def test_rejects_mismatch_between_book_and_consolidated_tests(self) -> None:
        source = packet.common.load_json(
            packet.ROOT / "content_tests" / "feofan_dukhovnaja_zhizn.json"
        )
        altered = copy.deepcopy(source)
        altered["chapters"][0]["test"][0]["question"] += "?"
        with tempfile.TemporaryDirectory() as temporary:
            tests_path = Path(temporary) / "tests.json"
            tests_path.write_text(
                json.dumps(altered, ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "не совпадают"):
                packet.render_packet(
                    packet.ROOT / "feofan_dukhovnaja_zhizn.json",
                    tests_path,
                    packet.ROOT / "content_tests" / "drafts",
                    "d" * 40,
                )


if __name__ == "__main__":
    unittest.main()
