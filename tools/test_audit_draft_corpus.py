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
        self.assertEqual(stats["correct_positions"], [2, 2, 2])

    def test_duplicate_prompt_in_another_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_root(root, duplicate_prompt=True)
            errors, _, _ = auditor.audit_corpus(
                root,
                auditor.DraftCorpus("sample", 2, 6),
            )

        self.assertTrue(any("вопрос повторяет" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
