import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import audit_book_tests as auditor


class AuditBookTestsTest(unittest.TestCase):
    def test_tell_does_not_match_inside_another_word(self) -> None:
        question = {
            "question": "Какое утверждение соответствует тексту?",
            "type": "choice",
            "answers": [
                {"text": "Первое краткое утверждение", "correct": True},
                {"text": "Настолько же краткое утверждение", "correct": False},
                {"text": "Третье краткое утверждение", "correct": False},
            ],
            "explanation": (
                "Пояснение содержит достаточно слов и раскрывает смысл выбранного "
                "утверждения без формальной подсказки в ответах."
            ),
        }
        errors: list[str] = []

        auditor.audit_question(question, "sample", errors, [])

        self.assertFalse(
            any("подсказка «только»" in message for message in errors),
            errors,
        )

    def test_documented_exclusion_completes_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "content_tests").mkdir()
            def question(correct_index: int) -> dict:
                return {
                    "question": (
                        f"Что проверяется в содержательной главе, вопрос {correct_index + 1}?"
                    ),
                    "type": "choice",
                    "answers": [
                        {
                            "text": f"{label} содержательный ответ",
                            "correct": index == correct_index,
                        }
                        for index, label in enumerate(("Первый", "Второй", "Третий"))
                    ],
                    "explanation": (
                        "Пояснение раскрывает смысл содержательной главы и остаётся "
                        "достаточно полным для строгого автоматического аудита."
                    ),
                }

            questions = [question(index) for index in range(3)]
            source = {
                "book_id": "sample",
                "chapters": [{"number": 1, "test": questions}],
                "excluded_chapters": [
                    {"number": 2, "reason": "Структурный заголовок без текста"}
                ],
            }
            book = {
                "id": "sample",
                "chapters": [
                    {"number": 1, "test": questions},
                    {"number": 2},
                ],
            }
            (root / "content_tests" / "sample.json").write_text(
                json.dumps(source, ensure_ascii=False), encoding="utf-8"
            )
            (root / "sample.json").write_text(
                json.dumps(book, ensure_ascii=False), encoding="utf-8"
            )

            output = io.StringIO()
            with patch.object(auditor, "ROOT", root), contextlib.redirect_stdout(output):
                result = auditor.main()

            self.assertEqual(result, 0, output.getvalue())
            self.assertIn("errors=0", output.getvalue())


if __name__ == "__main__":
    unittest.main()
