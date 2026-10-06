"""Data preservation and fail-closed checks for the frozen apparatus repair."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from tools.recover_feofan_put_notes import candidate_from_bytes

ROOT = Path(__file__).resolve().parents[1]


class RecoveryContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "feofan_put_ko_spaseniyu.json").read_bytes()
        cls.book = json.loads(cls.raw)
        cls.plan = json.loads((ROOT / "staging/feofan_notes_2026-10-05/recovery_plan.json").read_text())

    def test_real_book_retains_every_existing_field(self):
        candidate = candidate_from_bytes(self.raw, self.plan)
        self.assertEqual(candidate["version"], 6)
        self.assertEqual(sum(len(c.get("notes", [])) for c in candidate["chapters"]), 83)
        for before, after in zip(self.book["chapters"], candidate["chapters"]):
            self.assertEqual(before, {k: v for k, v in after.items() if k != "notes"})
        self.assertEqual({k: v for k, v in self.book.items() if k not in ["chapters", "version"]},
                         {k: v for k, v in candidate.items() if k not in ["chapters", "version"]})

    def test_changed_active_bytes_refused(self):
        with self.assertRaises(ValueError):
            candidate_from_bytes(self.raw + b" ", self.plan)

    def test_missing_note_refused(self):
        plan = deepcopy(self.plan)
        plan["notes"].pop(40)
        with self.assertRaises(ValueError):
            candidate_from_bytes(self.raw, plan)

    def test_duplicate_and_reordered_notes_refused(self):
        for duplicate in [True, False]:
            plan = deepcopy(self.plan)
            if duplicate:
                plan["notes"][1]["source_id"] = "note1"
            else:
                plan["notes"][0], plan["notes"][1] = plan["notes"][1], plan["notes"][0]
            with self.subTest(duplicate=duplicate), self.assertRaises(ValueError):
                candidate_from_bytes(self.raw, plan)

    def test_changed_note_location_refused(self):
        plan = deepcopy(self.plan)
        plan["notes"][0]["paragraph"] += 1
        with self.assertRaises(ValueError):
            candidate_from_bytes(self.raw, plan)

    def test_out_of_bounds_location_refused(self):
        plan = deepcopy(self.plan)
        plan["notes"][0]["paragraph"] = 999
        with self.assertRaises(ValueError):
            candidate_from_bytes(self.raw, plan)

    def test_empty_note_refused(self):
        plan = deepcopy(self.plan)
        plan["notes"][0]["text"] = "   "
        with self.assertRaises(ValueError):
            candidate_from_bytes(self.raw, plan)

    def test_title_note_does_not_become_body_paragraph(self):
        candidate = candidate_from_bytes(self.raw, self.plan)
        chapter = candidate["chapters"][29]
        self.assertEqual(chapter["paragraphs"], self.book["chapters"][29]["paragraphs"])
        self.assertTrue(chapter["notes"][0].startswith("Начало взято из:"))
        self.assertEqual(len(chapter["paragraphs"]), 39)


if __name__ == "__main__":
    unittest.main()
