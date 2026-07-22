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


if __name__ == "__main__":
    unittest.main()
