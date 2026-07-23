import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import audit_draft_tests as auditor


class AuditDraftTestsTest(unittest.TestCase):
    def test_partial_editorial_batch_is_valid_without_full_book_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book = {
                "id": "sample",
                "chapters": [{"number": 1}, {"number": 2}],
            }
            draft = {
                "book_id": "sample",
                "chapters": [
                    {
                        "number": 1,
                        "test": [
                            {
                                "question": f"Что проверяет вопрос номер {index + 1}?",
                                "type": "choice",
                                "answers": [
                                    {
                                        "text": f"{label} содержательный ответ",
                                        "correct": answer_index == index,
                                    }
                                    for answer_index, label in enumerate(
                                        ("Первый", "Второй", "Третий")
                                    )
                                ],
                                "explanation": (
                                    "Пояснение раскрывает смысл главы и содержит достаточно "
                                    "слов для полноценной автоматической проверки материала."
                                ),
                            }
                            for index in range(3)
                        ],
                    }
                ],
            }
            (root / "sample.json").write_text(
                json.dumps(book, ensure_ascii=False), encoding="utf-8"
            )
            draft_path = root / "draft.json"
            draft_path.write_text(
                json.dumps(draft, ensure_ascii=False), encoding="utf-8"
            )

            with patch.object(auditor, "ROOT", root):
                errors, warnings, chapters, questions = auditor.audit_draft(
                    draft_path
                )

            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])
            self.assertEqual(chapters, 1)
            self.assertEqual(questions, 3)


if __name__ == "__main__":
    unittest.main()
