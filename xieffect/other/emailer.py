from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from os import urandom
from random import randint
from smtplib import SMTPDataError

from flask_mail import Message
from itsdangerous import URLSafeSerializer, BadSignature

from common import mail, app
from .discorder import send_message as send_discord_message, WebhookURLs

EMAIL_FOLDER: str = "../static/emails/"
SALT: str = app.config["SECURITY_PASSWORD_SALT"]


def create_random_serializer():
    return URLSafeSerializer(urandom(randint(32, 64)))


@dataclass()
class EmailTypeData:
    theme: str
    filename: str
    serializer: URLSafeSerializer = field(default_factory=create_random_serializer)

    def generate_code(self, payload: str) -> str:
        return self.serializer.dumps(payload, salt=SALT)

    def parse_code(self, code: str) -> str | None:
        try:
            return self.serializer.loads(code, salt=SALT)
        except BadSignature:
            return None


class EmailType(EmailTypeData, Enum):
    CONFIRM = ("Подтверждение адреса электронной почты на xieffect.ru", "registration-email.html")
    CHANGE = ("Смена адреса электронной почты на xieffect.ru", "registration-email.html")
    PASSWORD = ("Смена пароля на xieffect.ru", "password-reset-email.html")


def generate_email(receiver: str, code: str, filename: str, theme: str) -> Message:
    with open(EMAIL_FOLDER + filename, "rb") as f:
        html: str = f.read().decode("utf-8").replace("&code", code)

    return Message(theme, recipients=[receiver], html=html)


def send_email(receiver: str, code: str, filename: str, theme: str):
    try:
        mail.send(generate_email(receiver, code, filename, theme))
    except SMTPDataError as e:
        print(e)
        send_discord_message(WebhookURLs.MAILBT, f"Email for {receiver} not sent:\n```{e}```")


def send_code_email(receiver: str, email_type: EmailType):
    return send_email(receiver, email_type.generate_code(receiver), email_type.filename, email_type.theme)
