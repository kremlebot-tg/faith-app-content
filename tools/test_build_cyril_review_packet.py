import unittest

from tools import build_cyril_review_packet as packet


class CyrilReviewPacketTest(unittest.TestCase):
    def test_packet_has_complete_stable_coverage(self) -> None:
        rendered = packet.render_packet(
            packet.ROOT / f"{packet.BOOK_ID}.json",
            packet.ROOT / "content_tests" / "drafts",
            "a" * 40,
        )

        self.assertEqual(set(rendered), {
            "00_PACKET.md",
            "01_chapters_001_012.md",
            "02_chapters_013_024.md",
        })
        body = "\n".join(rendered.values())
        self.assertEqual(body.count("**Вердикт:**"), 72)
        for chapter in range(1, 25):
            for question in range(1, 4):
                self.assertEqual(
                    body.count(f"### КИ{chapter:03d}.{question}"),
                    1,
                )
        self.assertIn("человеческая\nбогословская рецензия пока ожидается", body)


if __name__ == "__main__":
    unittest.main()
