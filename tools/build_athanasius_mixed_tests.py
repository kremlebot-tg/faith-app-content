#!/usr/bin/env python3
"""Добавляет mixed-задания к «Слову о воплощении» святителя Афанасия."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOK_ID = "afanasij_voploshhenie"


def matching(prompt: str, pairs: tuple[tuple[str, str], ...], explanation: str) -> dict:
    return {
        "question": prompt,
        "type": "matching",
        "pairs": [{"left": left, "right": right} for left, right in pairs],
        "explanation": explanation,
    }


def ordering(prompt: str, items: tuple[str, ...], explanation: str) -> dict:
    return {
        "question": prompt,
        "type": "ordering",
        "items": list(items),
        "explanation": explanation,
    }


def cloze(
    question: str,
    prompt: str,
    answers: tuple[str, str, str],
    correct: int,
    explanation: str,
) -> dict:
    return {
        "question": question,
        "type": "cloze",
        "prompt": prompt,
        "answers": [
            {"text": text, "correct": index == correct}
            for index, text in enumerate(answers)
        ],
        "explanation": explanation,
    }


def main() -> None:
    target = ROOT / "content_tests" / f"{BOOK_ID}.json"
    data = json.loads(target.read_text(encoding="utf-8"))
    chapters = {chapter["number"]: chapter["test"] for chapter in data["chapters"]}
    chapters[1][0] = matching(
        "Соотнесите дары творения человека с их смыслом.",
        (
            ("Бытие из небытия", "получено от Творца"),
            ("Образ Божий", "призывает к общению со Словом"),
            ("Свободный ответ", "может хранить или отвергать дар"),
        ),
        "Человек не имеет бытия и нетления сам по себе. Бог творит его, сообщает Свой образ и призывает свободно пребывать в общении со Словом.",
    )
    chapters[2][1] = ordering(
        "Расположите ход рассуждения Афанасия о спасении от тления.",
        (
            "Человек отпадает от общения с Богом",
            "Тление и смерть овладевают человеческим естеством",
            "Божие Слово принимает человеческую природу",
            "Воскресение открывает путь к нетлению",
        ),
        "Покаяние необходимо, но само по себе не исцеляет природу от смерти. То же Слово, Которым человек сотворён, принимает человеческую природу и обновляет её через смерть и Воскресение.",
    )
    chapters[4][2] = matching(
        "Соотнесите обстоятельства Креста с их значением в рассуждении святителя.",
        (
            ("Публичная смерть", "подтверждает действительность страдания"),
            ("Крест, нанесённый врагами", "показывает добровольное принятие смерти"),
            ("Нетление тела", "свидетельствует о силе воплощённого Слова"),
        ),
        "Христос принимает действительную и видимую смерть, а не мнимое страдание. Крест не обнаруживает бессилие: воскресение того же тела являет победу Жизни над смертью.",
    )
    chapters[5][0] = cloze(
        "Что воскресение в третий день подтверждает о теле Христа?",
        "Умершее тело Христа восстало тем же и стало ___.",
        ("нетленным", "бестелесным", "неузнаваемым"),
        0,
        "Воскресение в третий день сохраняет две истины: тело Христа действительно умерло и оно же восстало. Победа над смертью не является заменой тела или отрицанием человечества Спасителя.",
    )
    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{target.name}: chapters={len(chapters)} questions=27")


if __name__ == "__main__":
    main()
