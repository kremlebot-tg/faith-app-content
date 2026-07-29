import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import audit_draft_tests as auditor


EXPLANATION = (
    "Объяснение связывает задание с содержанием главы и помогает осмысленно "
    "проверить понимание авторского наставления."
)


def structured_questions() -> list[dict]:
    return [
        {
            "type": "matching",
            "question": "Соотнесите образ и его смысл.",
            "pairs": [
                {"left": "Семя", "right": "Начало навыка"},
                {"left": "Корень", "right": "Устойчивая склонность"},
                {"left": "Плод", "right": "Видимый поступок"},
            ],
            "explanation": EXPLANATION,
        },
        {
            "type": "ordering",
            "question": "Восстановите последовательность рассуждения.",
            "items": ["Внимание", "Рассуждение", "Решение"],
            "explanation": EXPLANATION,
        },
        {
            "type": "cloze",
            "question": "Дополните краткое наставление.",
            "prompt": "Добрый навык требует ___.",
            "answers": [
                {"text": "внимания", "correct": True},
                {"text": "спешки", "correct": False},
            ],
            "explanation": EXPLANATION,
        },
    ]


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

    def test_partial_batch_accepts_three_structured_question_types(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.json").write_text(
                json.dumps(
                    {"id": "sample", "chapters": [{"number": 1}]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            draft_path = root / "draft.json"
            draft_path.write_text(
                json.dumps(
                    {
                        "book_id": "sample",
                        "chapters": [
                            {"number": 1, "test": structured_questions()}
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(auditor, "ROOT", root):
                errors, warnings, chapters, questions = auditor.audit_draft(
                    draft_path
                )

            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])
            self.assertEqual(chapters, 1)
            self.assertEqual(questions, 3)

    def test_unknown_question_type_is_reported_in_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.json").write_text(
                json.dumps(
                    {"id": "sample", "chapters": [{"number": 1}]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            questions = structured_questions()
            questions[1] = {
                "type": "mystery",
                "question": "Неизвестный формат.",
                "explanation": EXPLANATION,
            }
            draft_path = root / "draft.json"
            draft_path.write_text(
                json.dumps(
                    {
                        "book_id": "sample",
                        "chapters": [{"number": 1, "test": questions}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(auditor, "ROOT", root):
                errors, _, _, _ = auditor.audit_draft(draft_path)

            self.assertTrue(
                any("неизвестный тип задания" in error for error in errors),
                errors,
            )


if __name__ == "__main__":
    unittest.main()
