#!/usr/bin/env python3
"""Create the frozen, unpublished apparatus candidate without reimporting text.

No network, live payload, manifest, version URL, or release writes. Historical
authorship of the source's editorial notes remains a separate review question.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "staging/feofan_notes_2026-10-05"
BOOK = ROOT / "feofan_put_ko_spaseniyu.json"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def candidate_from_bytes(raw, plan):
    if digest(raw) != plan["base_sha256"]:
        raise ValueError("Active book changed; the note-location plan must be rechecked")
    original = json.loads(raw)
    if original["id"] != "feofan_put_ko_spaseniyu" or original["version"] != 5:
        raise ValueError("Unexpected active payload identity/version")
    if len(original["chapters"]) != 33 or sum(len(c["paragraphs"]) for c in original["chapters"]) != 705:
        raise ValueError("Unexpected chapter/paragraph structure")
    if any(c.get("notes") for c in original["chapters"]):
        raise ValueError("Refusing to overwrite or duplicate an existing apparatus")
    notes = plan["notes"]
    if [n["source_id"] for n in notes] != [f"note{x}" for x in range(1, 84)]:
        raise ValueError("Incomplete, duplicate, or reordered source apparatus")
    by_number = {c["number"]: c for c in original["chapters"]}
    if len(by_number) != 33:
        raise ValueError("Duplicate chapter numbers")
    for note in notes:
        chapter = by_number[note["chapter"]]
        index = note["paragraph"]
        if note["anchor_kind"] == "heading" and index == 0:
            anchor = chapter["title"]
        elif note["anchor_kind"] == "paragraph" and 1 <= index <= len(chapter["paragraphs"]):
            anchor = chapter["paragraphs"][index - 1]
        else:
            raise ValueError("Invalid note location")
        if digest(anchor.encode("utf-8")) != note["local_anchor_sha256"]:
            raise ValueError("The frozen note anchor does not match")
        if not note["text"].strip():
            raise ValueError("Empty note")
    candidate = deepcopy(original)
    candidate["version"] = 6
    target = {c["number"]: c for c in candidate["chapters"]}
    for note in notes:
        target[note["chapter"]].setdefault("notes", []).append(note["text"])
    # Every pre-existing chapter field and every body character must survive.
    reverse = deepcopy(candidate)
    reverse["version"] = original["version"]
    for chapter in reverse["chapters"]:
        if not by_number[chapter["number"]].get("notes"):
            chapter.pop("notes", None)
    if reverse != original:
        raise ValueError("Candidate altered an existing book field")
    return candidate


def main():
    if STAGE.resolve() != STAGE or BOOK.resolve() != BOOK:
        raise ValueError("Unexpected symlink target")
    plan = json.loads((STAGE / "recovery_plan.json").read_text())
    candidate = candidate_from_bytes(BOOK.read_bytes(), plan)
    raw = (json.dumps(candidate, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path = STAGE / BOOK.name
    if path.is_symlink() or (path.exists() and path.read_bytes() != raw):
        raise ValueError("Refusing to replace a different candidate")
    path.write_bytes(raw)
    print(json.dumps({"candidate": str(path.relative_to(ROOT)), "bytes": len(raw),
                      "sha256": digest(raw), "notes": 83, "published": False,
                      "historical_apparatus_review_complete": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
