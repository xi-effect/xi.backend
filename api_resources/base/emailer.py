from os import path, urandom
from random import randint
from typing import Optional, Dict, List
from base64 import urlsafe_b64encode
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from itsdangerous import URLSafeSerializer as USS, BadSignature as BS

from api_resources.base.discorder import send_discord_message, WebhookURLs

from main import app

email_folder: str = "files/emails/"
scopes: List[str] = ["https://mail.google.com/"]


class EmailSender:
    def __init__(self):
        self.credentials = Credentials.from_authorized_user_file("token.json", scopes) \
            if path.exists("token.json") else None
        self.service = None
        self.rebuild_service()
        self.sender = app.config["MAIL_USERNAME"]

    def rebuild_service(self):
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
                self.credentials = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                send_discord_message(WebhookURLs.WEIRDO, "Google API token has been re-written!")
                token.write(self.credentials.to_json())

        self.service = build("gmail", "v1", credentials=self.credentials)

    def generate_email(self, receiver: str, code: str, filename: str, theme: str):
        with open(email_folder + filename, "rb") as f:
            html: str = f.read().decode("utf-8").replace("&code", code)

        message = MIMEText(html, "html")
        message["to"] = receiver
        message["from"] = self.sender
        message["subject"] = theme

        return {"raw": urlsafe_b64encode(message.as_string().encode()).decode()}

    def generate_code_email(self, receiver: str, code_type: str, filename: str, theme: str):
        return self.generate_email(receiver, generate_code(receiver, code_type), filename, theme)

    def send(self, message):
        self.service.users().messages().send(userId="me", body=message).execute()


serializers: Dict[str, USS] = {k: USS(urandom(randint(32, 64))) for k in ["confirm", "change", "pass"]}
themes: Dict[str, str] = {
    "confirm": "Подтверждение адреса электронной почты на xieffect.ru",
    "change": "Смена адреса электронной почты на xieffect.ru",
    "pass": "Смена пароля на xieffect.ru"
}
salt: str = app.config["SECURITY_PASSWORD_SALT"]

try:
    sender: EmailSender = EmailSender()
except RefreshError as error:
    send_discord_message(WebhookURLs.ERRORS, "Google API token refresh failed again!")


def send_email(receiver: str, code: str, filename: str, theme: str):
    return sender.send(sender.generate_email(receiver, code, filename, theme))


def send_generated_email(receiver: str, code_type: str, filename: str):
    return sender.send(sender.generate_code_email(receiver, code_type, filename, themes[code_type]))


def generate_code(payload: str, code_type: str) -> str:
    return serializers[code_type].dumps(payload, salt=salt)


def parse_code(code: str, code_type: str) -> Optional[str]:
    try:
        return serializers[code_type].loads(code, salt=salt)
    except BS:
        return None


if __name__ == "__main__":
    send_generated_email("qwert45hi@yandex.ru", "confirm", "registration-email.html")
