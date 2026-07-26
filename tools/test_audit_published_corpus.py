import json
from pathlib import Path
import tempfile
import unittest

from tools import audit_published_corpus as auditor


def question(number: int, correct_index: int) -> dict:
    openings = (
        "Какой смысл раскрывает первый",
        "Почему автор вводит второй",
        "Чем в этой главе служит третий",
        "Что помогает понять четвёртый",
        "К чему приводит пятый",
        "Как раскрывается шестой пример",
    )
    return {
        "question": f"{openings[number - 1]} редакционный пример?",
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


class AuditPublishedCorpusTest(unittest.TestCase):
    def make_root(self, root: Path, duplicate_prompt: bool = False) -> None:
        drafts = root / "content_tests" / "drafts"
        drafts.mkdir(parents=True)
        (root / "manifest.json").write_text(
            json.dumps(
                {"library": [{"id": "first"}, {"id": "second"}]},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        first = [question(index + 1, index) for index in range(3)]
        second = [question(index + 4, index) for index in range(3)]
        if duplicate_prompt:
            second[0]["question"] = first[0]["question"]
        (root / "content_tests" / "first.json").write_text(
            json.dumps(
                {
                    "book_id": "first",
                    "chapters": [{"number": 1, "test": first}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (drafts / "second_01.json").write_text(
            json.dumps(
                {
                    "book_id": "second",
                    "chapters": [{"number": 1, "test": second}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def test_combined_and_partitioned_sources_pass_together(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_root(root)
            errors, warnings, stats = auditor.audit_published_corpus(root)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(stats["books"], 2)
        self.assertEqual(stats["questions"], 6)
        self.assertEqual(stats["correct_positions"], [2, 2, 2])

    def test_duplicate_prompt_between_books_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_root(root, duplicate_prompt=True)
            errors, _, _ = auditor.audit_published_corpus(root)

        self.assertTrue(any("вопрос повторяет" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
