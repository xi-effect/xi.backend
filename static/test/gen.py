from datetime import datetime, timedelta
from json import dump
from random import randint, shuffle, choice
from typing import Union

from lorem import sentence as lorem_sentence, paragraph as lorem_paragraph


def lorem_word():
    return lorem_sentence().partition(" ")[0]


def generate_page_bundle():
    def generate_component(practice: bool, blueprint: bool = False):
        return {
            "type": "quiz",
            "quizType": "single" if (single := randint(0, 1) * randint(1, answers := randint(3, 10))) else "multiple",
            "fontSize": randint(12, 20),
            "textAlign": "left",
            "fontWeight": "normal",
            "fontStyle": "normal",
            "textDecoration": "none",
            "content": [{"label": lorem_sentence()} for _ in range(answers)],
            "rightAnswers": [single] if single else [i for i in range(answers) if bool(randint(0, 1))],
            "userAnswer": [],
            "successAnswer": None
        }

    result = [{
        "id": i,
        "name": lorem_word() + " " + lorem_word().lower(),
        "description": lorem_paragraph() + " test",
        "theme": lorem_sentence(),
        "kind": "practice" if (practice := (seed := randint(0, 8)) % 2 == 0) else "theory",
        "blueprint": False,
        "reusable": bool(seed & 2),
        "public": bool(seed & 4),
        "components": [generate_component(practice) for _ in range(randint(1, 10))]
    } for i in range(10)]

    with open("page-bundle2.json", "w", encoding="utf-8") as f:  # temp 2!
        dump(result, f, ensure_ascii=False, indent=4)


def generate_user_bundle():
    result = [{
        "username": lorem_word().lower(),
        "name": lorem_word() if (seed := randint(0, 9)) > 2 else None,
        "surname": lorem_word() if seed > 4 else None,
        "patronymic": lorem_word() if seed > 7 else None,
    } for _ in range(10)]

    with open("user-bundle.json", "w", encoding="utf-8") as f:
        dump(result, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    pass
