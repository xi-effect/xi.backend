from datetime import datetime, timedelta
from json import dump
from random import randint, shuffle, choice
from typing import Union

from lorem import sentence, paragraph


def generate_user_bundle():
    result = [{
        "username": sentence().partition(" ")[0].lower(),
        "name": sentence().partition(" ")[0] if (seed := randint(0, 9)) > 2 else None,
        "surname": sentence().partition(" ")[0] if seed > 4 else None,
        "patronymic": sentence().partition(" ")[0] if seed > 7 else None,
        "bio": paragraph() if seed % 2 == 0 else None,
        "group": chr(65 + randint(0, 25)) + str(randint(1, 16)),
    } for _ in range(10)]

    with open("user-bundle.json", "w") as f:
        dump(result, f, indent=4)


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
            "name": sentence()[:randint(5, 30)],
            "owner-email": f"{owner_i}@user.user",
            "participants": participants,
            "messages": [{
                "content": paragraph()[:randint(1, 10) * 20],
                "sender-email": last_sender if randint(0, 1) == 1 else (last_sender := choice(user_emails)),
                "sent": (last_sent := last_sent + timedelta(minutes=randint(0, 20))).isoformat(),
                "updated": (last_sent + timedelta(hours=randint(0, 24))).isoformat() if randint(0, 1) == 1 else None,
            } for _ in range(70)],
        }

    with open("chat-bundle.json", "w") as f:
        dump([generate_chat(i) for i in range(4)], f, indent=4)


if __name__ == "__main__":
    generate_chat_bundle()
