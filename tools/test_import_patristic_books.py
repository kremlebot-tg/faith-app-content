import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import import_patristic_books as importer


class ImportPatristicBooksTest(unittest.TestCase):
    def test_note_anchors_are_removed_and_keep_their_chapter(self) -> None:
        page = """
        <h1>Книга</h1>
        <h2 class="text-center">Первая беседа</h2>
        <p class="txt">Первый текст<a href="#note1" id="note1_return"><sup>1</sup></a>.</p>
        <h2 class="text-center">Вторая беседа<a href="#footnote1" id="footnote1_return"><sup>*</sup></a></h2>
        <p class="txt">Второй текст.</p>
        <p class="after-text-vignette">* * *</p>
        <p class="h2">Примечания</p>
        <a id="note1"></a><div class="note"><a href="#note1_return"><sup>1</sup></a><p class="txt">Первое примечание.</p></div>
        <a id="footnote1"></a><div class="note"><a href="#footnote1_return"><sup>*</sup></a><p class="txt">Примечание об авторстве.</p></div>
        """

        _, raw_elements, notes = importer.ordered_elements(page)
        elements = importer.strip_note_section(raw_elements)

        self.assertEqual(notes, {
            "note1": "Первое примечание.",
            "footnote1": "Примечание об авторстве.",
        })
        self.assertEqual([element["text"] for element in elements], [
            "Первая беседа",
            "Первый текст.",
            "Вторая беседа",
            "Второй текст.",
        ])
        self.assertEqual(elements[1]["note_refs"], ["note1"])
        self.assertEqual(elements[2]["note_refs"], ["footnote1"])

    def test_missing_note_text_is_an_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "нет текста примечания"):
            importer.resolve_notes(["note7"], {}, "sample")

    def test_slice_from_anchor_stops_before_page_tail(self) -> None:
        page = (
            '<p>Предисловие.</p><a id="0_2"></a>'
            '<p id="p1">Текст поучения.</p>'
            '<div class="related-header">Рекомендации</div>'
        )

        fragment = importer._slice_from_anchor(page, "0_2")

        self.assertIn("Текст поучения.", fragment)
        self.assertNotIn("Предисловие.", fragment)
        self.assertNotIn("Рекомендации", fragment)

    def test_chapter_fragment_keeps_refs_and_attached_notes(self) -> None:
        fragment = """
        <p id="p1">Первый текст
        <a href="https://azbyka.ru/biblia/?Mt.1:1">Мф.1:1</a>
        <a href="#note1" id="note1_return"><sup>1</sup></a>.</p>
        <a id="note1"></a><div class="note"><p>Примечание.</p></div>
        """

        chapter, used_notes, note_count = importer._chapter_from_fragment(
            number=3,
            title="Поучение",
            fragment=fragment,
            context="sample:3",
        )

        self.assertEqual(chapter["number"], 3)
        self.assertEqual(chapter["paragraphs"], ["Первый текст Мф.1:1."])
        self.assertEqual(chapter["notes"], ["Примечание."])
        self.assertEqual(chapter["scripture_refs"][0]["text"], "Мф.1:1")
        self.assertEqual(used_notes, {"note1"})
        self.assertEqual(note_count, 1)

    def test_tests_only_preserves_existing_book_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "sample.json"
            original = {
                "id": "sample",
                "version": 1,
                "chapters_count": 1,
                "chapters": [{
                    "number": 1,
                    "title": "Глава",
                    "paragraphs": ["Проверенный текст."],
                    "scripture_refs": [],
                }],
            }
            path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")

            def attach(_book_id, chapters):
                chapters[0]["test"] = [{"question": "Вопрос?"}]

            with patch.object(importer, "attach_authored_tests", side_effect=attach):
                importer.embed_tests_in_existing_book(
                    {"id": "sample", "count": 1, "version": 2}, root
                )

            updated = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(updated["version"], 2)
            self.assertEqual(updated["chapters"][0]["paragraphs"], ["Проверенный текст."])
            self.assertEqual(updated["chapters"][0]["test"], [{"question": "Вопрос?"}])

    def test_numbered_pages_can_use_nonsequential_source_numbers(self) -> None:
        config = {
            "id": "sample",
            "count": 2,
            "url": "https://example.test/book",
            "source_numbers": [27, 31],
            "chapter_titles": ["Первое слово", "Пятое слово"],
            "expected_notes": 0,
        }
        pages = {
            "https://example.test/book/27": "<h1>Слово 27</h1><p>Текст 27.</p>",
            "https://example.test/book/31": "<h1>Слово 31</h1><p>Текст 31.</p>",
        }

        with (
            patch.object(importer, "fetch", side_effect=pages.__getitem__) as fetch,
            patch.object(importer.time, "sleep"),
        ):
            chapters = importer.build_numbered_page_chapters(config)

        self.assertEqual(
            [call.args[0] for call in fetch.call_args_list],
            list(pages),
        )
        self.assertEqual([chapter["number"] for chapter in chapters], [1, 2])
        self.assertEqual(
            [chapter["title"] for chapter in chapters],
            ["Первое слово", "Пятое слово"],
        )

    def test_hesychasm_pages_strip_navigation_and_repair_transcription(self) -> None:
        config = {
            "id": "sample",
            "count": 1,
            "url": "https://example.test/txt",
        }
        page = """
        <h2>Слово первое. О жизни</h2>
        <p>Благодать Бо-жия и содела-лись живыми.</p>
        <p>Последний абзац. СОДЕРЖАНИЕ ВПЕРЕД http://www.hesychasm.ru/index.htm</p>
        <script>Md.write('<p>Счётчик</p>')</script></body>
        """

        with (
            patch.object(importer, "fetch_cp1251", return_value=page),
            patch.object(importer.time, "sleep"),
        ):
            chapters = importer.build_hesychasm_chapters(config)

        self.assertEqual(chapters[0]["title"], "О жизни")
        self.assertEqual(chapters[0]["paragraphs"], [
            "Благодать Божия и соделались живыми.",
            "Последний абзац.",
        ])


if __name__ == "__main__":
    unittest.main()
