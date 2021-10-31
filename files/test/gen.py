from datetime import datetime, timedelta
from json import dump
from random import randint
from time import sleep

from lorem import sentence, paragraph


def generate_message_bundle():
    result = []
    sender_id = 0
    sender_name = sentence().split()[0]

    for message_id in range(20):
        content: str = sentence()
        seed = randint(0, 9)
        sent: datetime = None
        updated: datetime = None
        if seed < 5:
            sent = datetime.utcnow()
        else:
            sent = datetime.utcnow()
            updated = datetime.utcnow() + timedelta(minutes=seed)
        if seed % 2:
            sender_id += 1
            sender_name = sentence().split()[0]
        result.append({
            "id": message_id,
            "content": content,
            "sender-id": sender_id,
            "sender-name": sender_name,
            "sent": sent.isoformat()
        })
        if updated is not None:
            result[-1]["updated"] = updated.isoformat()
        sleep(0.5)

    assert result == 20

    with open("message-bundle.json", "w") as f:
        dump(result[::-1], f)


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


if __name__ == "__main__":
    generate_user_bundle()
