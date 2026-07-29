import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import audit_book_tests as auditor


EXPLANATION = (
    "Объяснение связывает задание с прочитанной главой и помогает осмысленно "
    "проверить понимание авторского наставления."
)


def choice_question(*, explicit_type: bool = True, correct_index: int = 1) -> dict:
    question = {
        "question": "Какое утверждение передаёт смысл прочитанного наставления?",
        "answers": [
            {
                "text": f"{label} содержательное утверждение",
                "correct": index == correct_index,
            }
            for index, label in enumerate(("Первое", "Второе", "Третье"))
        ],
        "explanation": EXPLANATION,
    }
    if explicit_type:
        question["type"] = "choice"
    return question


def matching_question() -> dict:
    return {
        "type": "matching",
        "question": "Соотнесите образ и смысл наставления.",
        "pairs": [
            {"left": "Семя", "right": "Начало доброго навыка"},
            {"left": "Корень", "right": "Укрепившаяся склонность"},
            {"left": "Плод", "right": "Видимое действие человека"},
        ],
        "explanation": EXPLANATION,
    }


def ordering_question() -> dict:
    return {
        "type": "ordering",
        "question": "Восстановите последовательность духовной работы.",
        "items": [
            "Заметить помысл",
            "Рассудить о нём",
            "Отвергнуть зло",
            "Обратиться к молитве",
        ],
        "explanation": EXPLANATION,
    }


def cloze_question(*, correct_index: int = 2) -> dict:
    return {
        "type": "cloze",
        "question": "Дополните фразу из прочитанной главы.",
        "prompt": "Добрый навык укрепляется через ___.",
        "answers": [
            {"text": text, "correct": index == correct_index}
            for index, text in enumerate(
                ("случайность", "рассуждение", "упражнение", "любопытство")
            )
        ],
        "explanation": EXPLANATION,
    }


class AuditBookTestsTest(unittest.TestCase):
    def test_all_v2_question_types_and_legacy_choice_are_valid(self) -> None:
        cases = (
            (choice_question(explicit_type=False), 1),
            (choice_question(), 1),
            (matching_question(), None),
            (ordering_question(), None),
            (cloze_question(), 2),
        )
        for question, expected_position in cases:
            with self.subTest(question_type=question.get("type", "legacy-choice")):
                errors: list[str] = []
                warnings: list[str] = []
                result = auditor.audit_question(
                    question,
                    "sample",
                    errors,
                    warnings,
                )
                self.assertEqual(errors, [])
                self.assertEqual(warnings, [])
                self.assertEqual(result, expected_position)

    def test_structured_questions_do_not_require_question_mark(self) -> None:
        for question in (
            matching_question(),
            ordering_question(),
            cloze_question(),
        ):
            errors: list[str] = []
            auditor.audit_question(question, "sample", errors, [])
            self.assertFalse(
                any("знаком вопроса" in message for message in errors),
                errors,
            )

        malformed_choice = choice_question()
        malformed_choice["question"] = "Выберите верное утверждение."
        errors = []
        auditor.audit_question(malformed_choice, "sample", errors, [])
        self.assertTrue(any("знаком вопроса" in message for message in errors))

    def test_malformed_and_unknown_v2_questions_are_rejected_without_crash(
        self,
    ) -> None:
        duplicate_matching = matching_question()
        duplicate_matching["pairs"][2]["left"] = " семя "
        short_ordering = ordering_question()
        short_ordering["items"] = short_ordering["items"][:2]
        duplicate_ordering = ordering_question()
        duplicate_ordering["items"][-1] = "ЗАМЕТИТЬ ПОМЫСЛ"
        two_blank_cloze = cloze_question()
        two_blank_cloze["prompt"] = "Сначала ___, затем ___."
        duplicate_cloze = cloze_question()
        duplicate_cloze["answers"][3]["text"] = " УПРАЖНЕНИЕ "
        two_correct_cloze = cloze_question()
        two_correct_cloze["answers"][0]["correct"] = True

        cases = (
            ({"type": "unknown"}, "неизвестный тип задания"),
            ("не объект", "вопрос не является объектом"),
            (
                {**matching_question(), "pairs": matching_question()["pairs"][:2]},
                "ровно 3 пары",
            ),
            (duplicate_matching, "значения left"),
            (short_ordering, "от 3 до 5 элементов"),
            (duplicate_ordering, "элементы ordering должны быть уникальны"),
            (two_blank_cloze, "ровно один ___"),
            (duplicate_cloze, "варианты ответа не должны повторяться"),
            (two_correct_cloze, "ровно 1 correct:true"),
        )
        for question, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                errors: list[str] = []
                auditor.audit_question(question, "sample", errors, [])
                self.assertTrue(
                    any(expected_error in message for message in errors),
                    errors,
                )

    def test_common_text_rules_apply_to_every_question_type(self) -> None:
        for question in (
            choice_question(),
            matching_question(),
            ordering_question(),
            cloze_question(),
        ):
            damaged = json.loads(json.dumps(question, ensure_ascii=False))
            damaged["explanation"] = "Ты должен просто запомнить этот ответ."
            errors: list[str] = []
            auditor.audit_question(damaged, "sample", errors, [])
            self.assertTrue(any("прямое обращение" in message for message in errors))
            self.assertTrue(any("12–75 слов" in message for message in errors))

    def test_cloze_keeps_answer_marker_and_length_quality_checks(self) -> None:
        marker_question = cloze_question(correct_index=0)
        marker_question["answers"] = [
            {"text": "истинное внимание", "correct": True},
            {"text": "простое упражнение", "correct": False},
            {"text": "обычное рассуждение", "correct": False},
        ]
        marker_errors: list[str] = []
        auditor.audit_question(marker_question, "marker", marker_errors, [])
        self.assertTrue(
            any("слово-маркер «истин»" in message for message in marker_errors),
            marker_errors,
        )

        length_question = cloze_question(correct_index=0)
        length_question["answers"] = [
            {"text": "долгое внимательное ежедневное упражнение", "correct": True},
            {"text": "внимание", "correct": False},
            {"text": "рассуждение", "correct": False},
        ]
        length_errors: list[str] = []
        auditor.audit_question(length_question, "length", length_errors, [])
        self.assertTrue(
            any("единственный самый длинный" in message for message in length_errors),
            length_errors,
        )

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

    def test_bundled_book_uses_app_book_and_separate_tests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "faith-app-content"
            app_library = base / "faith_app" / "assets" / "library"
            (root / "content_tests").mkdir(parents=True)
            app_library.mkdir(parents=True)

            def question(correct_index: int) -> dict:
                return {
                    "question": (
                        f"Что проверяет вопрос встроенной книги номер {correct_index + 1}?"
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
                        "Пояснение раскрывает смысл встроенной книги и остаётся "
                        "достаточно полным для строгого автоматического аудита."
                    ),
                }

            questions = [question(index) for index in range(3)]
            source = {
                "book_id": "sample",
                "chapters": [{"number": 1, "test": questions}],
            }
            (root / "content_tests" / "sample.json").write_text(
                json.dumps(source, ensure_ascii=False),
                encoding="utf-8",
            )
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "library": [
                            {
                                "id": "sample",
                                "bundled": True,
                                "bundle_path": "assets/library/sample.json",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (app_library / "sample.json").write_text(
                json.dumps(
                    {"id": "sample", "chapters": [{"number": 1}]}
                ),
                encoding="utf-8",
            )
            (app_library / "sample_tests.json").write_text(
                json.dumps(source, ensure_ascii=False),
                encoding="utf-8",
            )

            output = io.StringIO()
            with patch.object(auditor, "ROOT", root), contextlib.redirect_stdout(output):
                result = auditor.main()

            self.assertEqual(result, 0, output.getvalue())
            self.assertIn("books=1", output.getvalue())

    def test_bundled_book_is_audited_without_private_app_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "faith-app-content"
            (root / "content_tests").mkdir(parents=True)

            def question(correct_index: int) -> dict:
                return {
                    "question": (
                        f"Как раскрывается смысл встроенной книги, вопрос {correct_index + 1}?"
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
                        "Пояснение раскрывает смысл встроенной книги и остаётся "
                        "достаточно полным для строгого автоматического аудита."
                    ),
                }

            source = {
                "book_id": "sample",
                "chapters": [
                    {
                        "number": 1,
                        "test": [question(index) for index in range(3)],
                    }
                ],
                "excluded_chapters": [
                    {"number": 2, "reason": "Структурное примечание без урока"}
                ],
            }
            (root / "content_tests" / "sample.json").write_text(
                json.dumps(source, ensure_ascii=False),
                encoding="utf-8",
            )
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "library": [
                            {
                                "id": "sample",
                                "bundled": True,
                                "bundle_path": "assets/library/sample.json",
                                "chapters_count": 2,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with patch.object(auditor, "ROOT", root), contextlib.redirect_stdout(output):
                result = auditor.main()

            self.assertEqual(result, 0, output.getvalue())
            self.assertIn("books=1", output.getvalue())
            self.assertIn("errors=0", output.getvalue())


if __name__ == "__main__":
    unittest.main()
