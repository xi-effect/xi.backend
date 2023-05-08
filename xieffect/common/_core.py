from __future__ import annotations

from json import dumps as dump_json, load as load_json
from os import getenv
from sys import modules

from dotenv import load_dotenv
from flask import Response
from flask_fullstack import Flask as _Flask, SQLAlchemy
from flask_mail import Mail

from ._files import absolute_path, open_file  # noqa: WPS436


class Flask(_Flask):
    def return_error(self, code: int, message: str):
        return Response(dump_json({"a": message}), code)

    def configure_jwt_with_loaders(self, *args, **kwargs) -> None:
        from .users_db import BlockedToken

        jwt = super().configure_jwt_with_loaders(*args, **kwargs)

        @jwt.token_in_blocklist_loader
        def check_if_token_revoked(_, jwt_payload) -> bool:
            return BlockedToken.find_by_jti(jwt_payload["jti"]) is not None


# xieffect specific:
load_dotenv(absolute_path(".env"))

with open_file("static/versions.json") as f:
    versions = load_json(f)

app: Flask = Flask(
    __name__,
    static_folder=absolute_path("static/public/"),
    static_url_path="/static/",
    versions=versions,
)

app.config["TESTING"] = "pytest" in modules
app.config["RESTX_INCLUDE_ALL_MODELS"] = True
app.secrets_from_env("hope it's local")
# TODO DI to use secrets in `URLSafeSerializer`s
app.configure_cors()

db_url: str = getenv(
    "DB_LINK", "sqlite:///" + absolute_path("xieffect/app.db")  # noqa: WPS336
)
db = SQLAlchemy(app, db_url)  # echo=True
Base = db.Model

mail_hostname: str | None = getenv("MAIL_HOSTNAME")
mail_username: str | None = getenv("MAIL_USERNAME")
mail_password: str | None = getenv("MAIL_PASSWORD")
mail_initialized = all((mail_hostname, mail_username, mail_hostname))
if mail_initialized:  # TODO pragma: no coverage (action)
    app.config["MAIL_SERVER"] = mail_hostname
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USERNAME"] = mail_username
    app.config["MAIL_DEFAULT_SENDER"] = mail_username
    app.config["MAIL_PASSWORD"] = mail_password
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USE_SSL"] = False
mail: Mail = Mail(app)
