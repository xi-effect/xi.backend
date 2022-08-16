from json import dumps
from os import getenv
from sys import modules
from typing import Type

from flask import Response
from flask_mail import Mail
from sqlalchemy import MetaData, create_engine

from __lib__.flask_fullstack import Flask as _Flask, configure_whooshee, Sessionmaker, IndexService
from __lib__.flask_fullstack.sqlalchemy import ModBase, create_base, Session


class Flask(_Flask):
    def return_error(self, code: int, message: str):
        return Response(dumps({"a": message}), code)

    def configure_jwt_with_loaders(self, *args, **kwargs) -> None:
        from .users_db import BlockedToken
        jwt = super().configure_jwt_with_loaders(*args, **kwargs)

        @jwt.token_in_blocklist_loader
        @sessionmaker.with_begin
        def check_if_token_revoked(_, jwt_payload, session):
            return BlockedToken.find_by_jti(session, jwt_payload["jti"]) is not None


def init_xieffect() -> tuple[str, MetaData, Type[ModBase], Sessionmaker, IndexService, dict, Flask, bool, Mail]:
    # xieffect specific:

    from dotenv import load_dotenv
    from json import load

    load_dotenv("../.env")

    convention = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }

    db_url: str = getenv("DB_LINK", "sqlite:///app.db")
    engine = create_engine(db_url, pool_recycle=280)  # echo=True
    db_meta = MetaData(bind=engine, naming_convention=convention)  # TODO allow naming conventions in FFS
    Base = create_base(db_meta)
    sessionmaker = Sessionmaker(bind=engine, class_=Session)

    index_service = configure_whooshee(sessionmaker, "../files/temp/whoosh")
    # configure_logging({
    #     "version": 1,
    #     "formatters": {"default": {
    #         "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
    #     }},
    #     "handlers": {"wsgi": {
    #         "class": "logging.StreamHandler",
    #         "stream": "ext://flask.logging.wsgi_errors_stream",
    #         "formatter": "default"
    #     }},
    #     "root": {
    #         "level": "DEBUG",
    #         "handlers": ["wsgi"]
    #     }
    # })

    versions = load(open("../static/versions.json", encoding="utf-8"))

    app: Flask = Flask(__name__, static_folder="../../static/public/", static_url_path="/static/", versions=versions)
    app.config["TESTING"] = "pytest" in modules.keys()
    app.secrets_from_env("hope it's local")  # TODO DI to use secrets in `URLSafeSerializer`s
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

    return db_url, db_meta, Base, sessionmaker, index_service, versions, app, mail_initialized, Mail(app)


db_url, db_meta, Base, sessionmaker, index_service, versions, app, mail_initialized, mail = init_xieffect()
app.config["RESTX_INCLUDE_ALL_MODELS"] = True
