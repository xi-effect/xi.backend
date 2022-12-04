from json import dump
from random import randint

from lorem import sentence as lorem_sentence


def lorem_word():
    return lorem_sentence().partition(" ")[0]


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
