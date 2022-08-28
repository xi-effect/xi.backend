from __future__ import annotations

from dataclasses import dataclass, field
from os import urandom
from random import SystemRandom
from smtplib import SMTPDataError

from flask_mail import Message
from flask_restx import Resource
from itsdangerous import URLSafeSerializer, BadSignature

from common import mail, app, User, mail_initialized, TypeEnum
from .discorder import send_message as send_discord_message, WebhookURLs

safe_random = SystemRandom()
EMAIL_FOLDER: str = "../static/emails/"
SALT: str = app.config["SECURITY_PASSWORD_SALT"]


def create_random_serializer():
    return URLSafeSerializer(urandom(safe_random.randint(32, 64)))


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


class EmailType(EmailTypeData, TypeEnum):
    CONFIRM = (
        "Подтверждение адреса электронной почты на xieffect.ru",
        "registration-email.html",
    )
    CHANGE = (
        "Смена адреса электронной почты на xieffect.ru",
        "email-change-email.html",
    )
    PASSWORD = (
        "Смена пароля на xieffect.ru",
        "password-reset-email.html",
    )


def generate_email(receiver: str, code: str, filename: str, theme: str) -> Message:
    with open(EMAIL_FOLDER + filename, "rb") as f:
        html: str = f.read().decode("utf-8").replace("&code", code)

    return Message(theme, recipients=[receiver], html=html)


def send_email(receiver: str, code: str, filename: str, theme: str):
    if not mail_initialized:
        return
    try:
        mail.send(generate_email(receiver, code, filename, theme))
    except SMTPDataError as e:
        print(e)
        send_discord_message(
            WebhookURLs.MAILBT, f"Email for {receiver} not sent:\n```{e}```"
        )


def send_code_email(receiver: str, email_type: EmailType) -> str:
    code = email_type.generate_code(receiver)
    send_email(receiver, code, email_type.filename, email_type.theme)
    return code


def create_email_confirmer(controller, route: str, email_type: EmailType):
    @controller.route(route + "<code>/")
    class EmailConfirmer(Resource):
        @controller.doc_abort(400, "Invalid code")
        @controller.with_begin
        @controller.a_response()
        def post(self, session, code: str) -> str:
            email = email_type.parse_code(code)
            user = None if email is None else User.find_by_email_address(session, email)
            if user is None:
                controller.abort(400, "Invalid code")
            user.email_confirmed = True
            return "Success"

    return EmailConfirmer
