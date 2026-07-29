import json
from pathlib import Path
import tempfile
import unittest

from tools import audit_draft_corpus as auditor


def question(number: int, correct_index: int) -> dict:
    openings = (
        "Какой смысл раскрывает",
        "Почему автор вводит",
        "Чем в этой главе служит",
        "Что помогает понять",
        "Как следует истолковать",
        "К чему приводит",
    )
    return {
        "question": f"{openings[number - 1]} редакционный пример номер {number}?",
        "type": "choice",
        "answers": [
            {
                "text": f"{label} содержательный вариант номер {number}",
                "correct": index == correct_index,
            }
            for index, label in enumerate(("Первый", "Второй", "Третий"))
        ],
        "explanation": (
            f"Объяснение номер {number} раскрывает содержание исходной главы "
            "и даёт читателю достаточно материала для осмысленного ответа."
        ),
    }


def mixed_question(number: int) -> dict:
    if number in (1, 5):
        return question(number, 0 if number == 1 else 1)
    base = question(number, 0)
    common = {
        "question": base["question"].rstrip("?") + ".",
        "explanation": base["explanation"],
    }
    if number == 2:
        return {
            **common,
            "type": "matching",
            "pairs": [
                {"left": "Начало 2", "right": "Первый смысл 2"},
                {"left": "Середина 2", "right": "Второй смысл 2"},
                {"left": "Завершение 2", "right": "Третий смысл 2"},
            ],
        }
    if number == 4:
        return {
            **common,
            "type": "ordering",
            "items": ["Первый этап 4", "Второй этап 4", "Третий этап 4"],
        }
    correct_index = 2 if number == 3 else 3
    return {
        **common,
        "type": "cloze",
        "prompt": f"Редакционный пример {number} требует ___.",
        "answers": [
            {
                "text": f"{label} вариант {number}",
                "correct": index == correct_index,
            }
            for index, label in enumerate(
                ("Первый", "Второй", "Третий", "Четвёртый")
            )
        ],
    }


class AuditDraftCorpusTest(unittest.TestCase):
    def make_root(self, root: Path, duplicate_prompt: bool = False) -> None:
        (root / "content_tests" / "drafts").mkdir(parents=True)
        (root / "sample.json").write_text(
            json.dumps(
                {
                    "id": "sample",
                    "chapters": [{"number": 1}, {"number": 2}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        first = [question(index + 1, index) for index in range(3)]
        second = [question(index + 4, index) for index in range(3)]
        if duplicate_prompt:
            second[0]["question"] = first[0]["question"]
        for filename, number, questions in (
            ("sample_01.json", 1, first),
            ("sample_02.json", 2, second),
        ):
            (root / "content_tests" / "drafts" / filename).write_text(
                json.dumps(
                    {
                        "book_id": "sample",
                        "chapters": [{"number": number, "test": questions}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

    def test_complete_corpus_passes_across_multiple_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_root(root)
            errors, warnings, stats = auditor.audit_corpus(
                root,
                auditor.DraftCorpus("sample", 2, 6),
            )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(stats["keyed_positions"], [2, 2, 2])
        self.assertEqual(stats["fourth_keyed_answers"], 0)

    def test_duplicate_prompt_in_another_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_root(root, duplicate_prompt=True)
            errors, _, _ = auditor.audit_corpus(
                root,
                auditor.DraftCorpus("sample", 2, 6),
            )

        self.assertTrue(any("вопрос повторяет" in error for error in errors))

    def test_mixed_corpus_tracks_only_choice_and_cloze_positions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "content_tests" / "drafts").mkdir(parents=True)
            (root / "sample.json").write_text(
                json.dumps(
                    {
                        "id": "sample",
                        "chapters": [{"number": 1}, {"number": 2}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            for filename, number, questions in (
                (
                    "sample_01.json",
                    1,
                    [mixed_question(index) for index in range(1, 4)],
                ),
                (
                    "sample_02.json",
                    2,
                    [mixed_question(index) for index in range(4, 7)],
                ),
            ):
                (root / "content_tests" / "drafts" / filename).write_text(
                    json.dumps(
                        {
                            "book_id": "sample",
                            "chapters": [{"number": number, "test": questions}],
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )

            errors, warnings, stats = auditor.audit_corpus(
                root,
                auditor.DraftCorpus("sample", 2, 6),
            )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(stats["keyed_positions"], [1, 1, 1])
        self.assertEqual(stats["fourth_keyed_answers"], 1)
        self.assertEqual(
            stats["question_types"],
            {"choice": 2, "matching": 1, "ordering": 1, "cloze": 2},
        )

    def test_unknown_type_in_corpus_is_rejected_without_crash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_root(root)
            path = root / "content_tests" / "drafts" / "sample_01.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["chapters"][0]["test"][0]["type"] = "mystery"
            path.write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8",
            )
            errors, _, stats = auditor.audit_corpus(
                root,
                auditor.DraftCorpus("sample", 2, 6),
            )

        self.assertTrue(
            any("неизвестный тип задания" in error for error in errors),
            errors,
        )
        self.assertEqual(stats["questions"], 6)


if __name__ == "__main__":
    unittest.main()
