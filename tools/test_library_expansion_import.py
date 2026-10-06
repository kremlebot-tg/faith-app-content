import unittest
from unittest.mock import patch

from tools import import_patristic_books as importer


class LibraryExpansionImportTest(unittest.TestCase):
    def test_editorial_breaks_preserve_every_word_and_original_boundaries(self):
        chapters = [{"number": 1, "paragraphs": [
            "Первый тезис. Далее начинается пример.", "Последний абзац."
        ]}]
        importer.apply_reading_breaks(chapters, {1: ["Далее начинается"]})
        self.assertEqual(chapters[0]["paragraphs"], [
            "Первый тезис.", "Далее начинается пример.", "Последний абзац."
        ])

    def test_changed_or_ambiguous_break_is_rejected(self):
        for paragraphs in [["Другой текст."], ["Пример. Далее. Далее."]]:
            with self.subTest(paragraphs=paragraphs):
                with self.assertRaises(ValueError):
                    importer.apply_reading_breaks([
                        {"number": 1, "paragraphs": paragraphs}
                    ], {1: ["Далее"]})

    def setUp(self):
        self.config = {
            "id": "sample", "url": "https://example.invalid/book",
            "source_start": r'<p id="p1">', "source_end": '<footer>',
            "chapter_label": "Глава", "count": 2,
        }
        self.page = '''<h1>Книга</h1><p>Современная аннотация</p>
        <p id="p1"><b>1</b>. Первая часть.</p>
        <p>Продолжение с <a href="/biblia/?Mt.5:1">Мф. 5:1</a>.</p>
        <p id="p2"><b>2</b>. Вторая часть.</p><footer><p>Источник и меню</p>'''

    def test_preserves_unnumbered_continuation_and_excludes_site_material(self):
        with patch.object(importer, "fetch", return_value=self.page):
            chapters = importer.build_numbered_paragraph_chapters(self.config)
        self.assertEqual([c["number"] for c in chapters], [1, 2])
        self.assertEqual(chapters[0]["paragraphs"], [
            "Первая часть.", "Продолжение с Мф. 5:1."])
        self.assertEqual(chapters[1]["paragraphs"], ["Вторая часть."])
        self.assertEqual(chapters[0]["scripture_refs"][0]["url"],
                         "https://azbyka.ru/biblia/?Mt.5:1")

    def test_missing_bounds_and_numbering_fail_closed(self):
        for broken in [self.page.replace('<p id="p1">', '<p>'),
                       self.page.replace('<footer>', ''),
                       self.page.replace('<b>2</b>', '<b>3</b>'),
                       self.page.replace('<b>2</b>', '<b>1</b>')]:
            with self.subTest(page=broken):
                with patch.object(importer, "fetch", return_value=broken):
                    with self.assertRaises(ValueError):
                        importer.build_numbered_paragraph_chapters(self.config)

    def test_new_notes_require_editorial_handling(self):
        page = self.page.replace('Первая часть.',
            'Первая часть<a href="#note1" id="note1_return">1</a>.')
        with patch.object(importer, "fetch", return_value=page):
            with self.assertRaises(ValueError):
                importer.build_numbered_paragraph_chapters(self.config)

    def test_only_exact_editorial_intros_are_excluded(self):
        config = dict(self.config, source_start=r'<h2 class="title">',
            heading_pattern=r'<(h2)\b[^>]*>(.*?)</\1>',
            excluded_chapter_intros=["Аннотация редакции."], count=1)
        page = '''<p>Меню</p><h2 class="title">Слово I</h2>
        <p>Аннотация редакции.</p><p>Авторский текст.</p><footer><p>Меню</p>'''
        with patch.object(importer, "fetch", return_value=page):
            chapters = importer.build_heading_chapters(config)
        self.assertEqual(chapters[0]["paragraphs"], ["Авторский текст."])
        with patch.object(importer, "fetch", return_value=page.replace(
                'Аннотация редакции.', 'Неизвестный новый текст.')):
            with self.assertRaises(ValueError):
                importer.build_heading_chapters(config)


if __name__ == "__main__":
    unittest.main()
