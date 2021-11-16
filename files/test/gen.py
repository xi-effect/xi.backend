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
            "content": [{
                "label": lorem_sentence(),
                "rightAnswer": single == i if single else bool(randint(0, 1)),
                "userAnswer": False,
            } for i in range(answers)],
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
        "bio": lorem_paragraph() if seed % 2 == 0 else None,
        "group": chr(65 + randint(0, 25)) + str(randint(1, 16)),
        "avatar": {
            "accessory": randint(0, 9),
            "body": randint(0, 27),
            "face": randint(0, 32),
            "hair": randint(0, 46),
            "facialHair": randint(0, 16),
            "bgcolor": randint(0, 12),
        }
    } for _ in range(10)]

    with open("user-bundle.json", "w", encoding="utf-8") as f:
        dump(result, f, ensure_ascii=False, indent=4)


def generate_chat_bundle():
    roles = ["basic", "basic", "basic", "admin", "muted", "muted", "muted", "basic", "moder", "moder"]
    demo_roles = ["moder", "muted", "admin", "basic"]

    def generate_chat(counter: int):
        owner_i: int = randint(0, 9)
        user_emails: list[Union[str, tuple[str, str]]] = [f"{i}@user.user" for i in range(10) if i != owner_i]
        shuffle(user_emails)
        participants = [(t, choice(roles[:counter * 3 + 1])) for t in user_emails[:counter * 3]]
        participants.append((f"{owner_i}@user.user", "owner"))
        participants.append(("test@test.test", demo_roles.pop()))

        last_sender = choice(user_emails)
        last_sent = datetime.utcnow()

        return {
            "name": lorem_sentence()[:randint(5, 30)],
            "owner-email": f"{owner_i}@user.user",
            "participants": participants,
            "messages": [{
                "content": lorem_paragraph()[:randint(1, 10) * 20],
                "sender-email": last_sender if randint(0, 1) == 1 else (last_sender := choice(user_emails)),
                "sent": (last_sent := last_sent + timedelta(minutes=randint(0, 20))).isoformat(),
                "updated": (last_sent + timedelta(hours=randint(0, 24))).isoformat() if randint(0, 1) == 1 else None,
            } for _ in range(70)],
        }

    with open("chat-bundle.json", "w", encoding="utf-8") as f:
        dump([generate_chat(i) for i in range(4)], f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    pass
