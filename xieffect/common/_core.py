from __future__ import annotations

from json import dumps as dump_json, load as load_json
from os import getenv
from sys import modules
from typing import TypeVar

from dotenv import load_dotenv
from flask import Response
from flask_fullstack import (
    configure_whooshee,
    Flask as _Flask,
    IndexService,
    ModBaseMeta,
)
from flask_mail import Mail
from flask_sqlalchemy import Model
from sqlalchemy import MetaData, select
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import Select

from ._files import absolute_path, open_file  # noqa: WPS436
from ._fsqla import SQLAlchemy  # noqa: WPS436


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

convention = {
    "ix": "ix_%(column_0_label)s",  # noqa: WPS323
    "uq": "uq_%(table_name)s_%(column_0_name)s",  # noqa: WPS323
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # noqa: WPS323
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # noqa: WPS323
    "pk": "pk_%(table_name)s",  # noqa: WPS323
}  # TODO allow naming conventions in FFS

db_url: str = getenv("DB_LINK", "sqlite:///" + absolute_path("xieffect/app.db"))
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
db_meta = MetaData(naming_convention=convention)
db = SQLAlchemy(
    app,
    metadata=db_meta,
    model_class=declarative_base(cls=Model, metaclass=ModBaseMeta),
    engine_options={"pool_recycle": 280},  # "echo": True
)

app.config["TESTING"] = "pytest" in modules
app.secrets_from_env("hope it's local")
# TODO DI to use secrets in `URLSafeSerializer`s
app.configure_cors()

mail_hostname = getenv("MAIL_HOSTNAME")
mail_username = getenv("MAIL_USERNAME")
mail_password = getenv("MAIL_PASSWORD")
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

t = TypeVar("t", bound="Base")


class Base(db.Model):  # TODO this is just an idea  # TODO pragma: no cover
    __abstract__ = True

    @classmethod
    def create(cls: type[t], **kwargs) -> t:
        entry = cls(**kwargs)
        db.session.add(entry)
        db.session.flush()
        return entry

    @classmethod
    def select_by_kwargs(cls, *order_by, **kwargs) -> Select:
        if len(order_by) == 0:
            return select(cls).filter_by(**kwargs)
        return select(cls).filter_by(**kwargs).order_by(*order_by)

    @classmethod
    def find_first_by_kwargs(cls: type[t], *order_by, **kwargs) -> t | None:
        return db.session.get_first(cls.select_by_kwargs(*order_by, **kwargs))

    @classmethod
    def find_all_by_kwargs(cls: type[t], *order_by, **kwargs) -> list[t]:
        return db.session.get_all(cls.select_by_kwargs(*order_by, **kwargs))

    @classmethod
    def find_paginated_by_kwargs(
        cls: type[t], offset: int, limit: int, *order_by, **kwargs
    ) -> list[t]:
        return db.session.get_paginated(
            cls.select_by_kwargs(*order_by, **kwargs), offset, limit
        )

    def delete(self) -> None:
        db.session.delete(self)
        db.session.flush()


app.config["RESTX_INCLUDE_ALL_MODELS"] = True
