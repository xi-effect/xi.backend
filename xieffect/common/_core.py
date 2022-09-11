from __future__ import annotations

from json import dumps as dump_json
from os import getenv
from sys import modules

from flask import Response
from flask_mail import Mail
from flask_sqlalchemy import Model
from sqlalchemy import MetaData, select
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import Select

from __lib__.flask_fullstack import (
    configure_whooshee,
    Flask as _Flask,
    IndexService,
    ModBaseMeta,
)
from common._fsqla import SQLAlchemy  # noqa: WPS436


class Flask(_Flask):
    def return_error(self, code: int, message: str):
        return Response(dump_json({"a": message}), code)

    def configure_jwt_with_loaders(self, *args, **kwargs) -> None:
        from .users_db import BlockedToken

        jwt = super().configure_jwt_with_loaders(*args, **kwargs)

        @jwt.token_in_blocklist_loader
        @sessionmaker.with_begin
        def check_if_token_revoked(_, jwt_payload, session) -> bool:
            return BlockedToken.find_by_jti(session, jwt_payload["jti"]) is not None


def init_xieffect() -> tuple[  # noqa: WPS210, WPS320
    str,
    SQLAlchemy,
    IndexService,
    dict,
    Flask,
    bool,
    Mail,
]:
    # xieffect specific:

    from dotenv import load_dotenv
    from json import load as load_json

    load_dotenv("../.env")

    with open("../static/versions.json", encoding="utf-8") as f:
        versions = load_json(f)

    app: Flask = Flask(
        __name__,
        static_folder="../../static/public/",
        static_url_path="/static/",
        versions=versions,
    )

    convention = {
        "ix": "ix_%(column_0_label)s",  # noqa: WPS323
        "uq": "uq_%(table_name)s_%(column_0_name)s",  # noqa: WPS323
        "ck": "ck_%(table_name)s_%(constraint_name)s",  # noqa: WPS323
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # noqa: WPS323
        "pk": "pk_%(table_name)s",  # noqa: WPS323
    }  # TODO allow naming conventions in FFS

    db_url: str = getenv("DB_LINK", "sqlite:///../app.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db_meta = MetaData(naming_convention=convention)
    db = SQLAlchemy(
        app,
        metadata=db_meta,
        model_class=declarative_base(cls=Model, metaclass=ModBaseMeta),
        engine_options={"pool_recycle": 280},  # "echo": True
    )
    index_service = configure_whooshee(db.session, "../files/temp/whoosh")

    app.config["TESTING"] = "pytest" in modules
    app.secrets_from_env("hope it's local")
    # TODO DI to use secrets in `URLSafeSerializer`s
    app.configure_cors()

    mail_username = getenv("MAIL_USERNAME", None)
    mail_password = getenv("MAIL_PASSWORD", None)
    mail_initialized = mail_username is not None and mail_password is not None
    if mail_initialized:
        app.config["MAIL_SERVER"] = "smtp.yandex.ru"
        app.config["MAIL_PORT"] = 587
        app.config["MAIL_USERNAME"] = mail_username
        app.config["MAIL_DEFAULT_SENDER"] = mail_username
        app.config["MAIL_PASSWORD"] = mail_password
        app.config["MAIL_USE_TLS"] = True
        app.config["MAIL_USE_SSL"] = False

    return (
        db_url,
        db,
        index_service,
        versions,
        app,
        mail_initialized,
        Mail(app),
    )


(
    db_url,
    db,
    index_service,
    versions,
    app,
    mail_initialized,
    mail,
) = init_xieffect()
app.config["RESTX_INCLUDE_ALL_MODELS"] = True
