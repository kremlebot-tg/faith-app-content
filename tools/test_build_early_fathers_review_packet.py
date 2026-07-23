import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools import build_early_fathers_review_packet as packet


class EarlyFathersReviewPacketTest(unittest.TestCase):
    def test_repository_packet_has_complete_stable_ids_and_notes(self) -> None:
        rendered = packet.render_packet(packet.ROOT, "e" * 40)

        self.assertEqual(
            set(rendered),
            {
                "00_PACKET.md",
                "01_afanasij.md",
                "02_makarij_001_025.md",
                "03_makarij_026_050.md",
                "04_zlatoust.md",
            },
        )
        body = "\n".join(rendered.values())
        self.assertEqual(body.count("**Вердикт:**"), 204)
        self.assertEqual(body.count("**Итог "), 68)
        self.assertIn("### АВ001.1", body)
        self.assertIn("### МБ050.3", body)
        self.assertIn("### ИЗ009.3", body)
        self.assertIn("епископу Севериану Габальскому", body)
        self.assertIn("Атрибуция этой беседы", rendered["04_zlatoust.md"])

    def test_rejects_mismatch_between_book_and_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "content_tests").mkdir()
            for book_id in {
                config.book_id for config in packet.CONFIGS
            }:
                shutil.copy(packet.ROOT / f"{book_id}.json", root)
                shutil.copy(
                    packet.ROOT / "content_tests" / f"{book_id}.json",
                    root / "content_tests",
                )
            path = root / "content_tests" / "afanasij_voploshhenie.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            altered = copy.deepcopy(data)
            altered["chapters"][0]["test"][0]["question"] += "?"
            path.write_text(
                json.dumps(altered, ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "не совпадают"):
                packet.render_packet(root, "f" * 40)


if __name__ == "__main__":
    unittest.main()
