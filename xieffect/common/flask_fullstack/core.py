from datetime import timedelta, datetime, timezone
from logging.config import dictConfig
from os import getenv

from flask import Flask as _Flask, Response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt, set_access_cookies, create_access_token, get_jwt_identity
from flask_restx import Api
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import DeclarativeMeta, declarative_base

from .marshals import flask_restx_has_bad_design
from .sqlalchemy import Sessionmaker
from .whoosh import IndexService


class Flask(_Flask):
    def __init__(self, *args, versions, **kwargs):
        super().__init__(*args, **kwargs)
        self.versions = versions

    def secrets_from_env(self, default) -> None:
        for secret_name in ["SECRET_KEY", "SECURITY_PASSWORD_SALT", "JWT_SECRET_KEY", "API_KEY"]:
            self.config[secret_name] = getenv(secret_name, default)

    def configure_cors(self) -> None:
        CORS(self, supports_credentials=True)

    def configure_restx(self, use_jwt: bool = True) -> Api:
        self.config["PROPAGATE_EXCEPTIONS"] = True
        authorizations = {
            "jwt": {
                "type": "apiKey",
                "in": "cookie",
                "name": "access_token_cookie"
            }
        } if use_jwt else None
        api = Api(self, doc="/doc/", version=self.versions["API"], authorizations=authorizations)
        api.add_namespace(flask_restx_has_bad_design)  # TODO workaround
        return api

    def configure_jwt_manager(self, sessionmaker: Sessionmaker, location: list[str],
                              access_expires: timedelta) -> JWTManager:
        self.config["JWT_TOKEN_LOCATION"] = location
        self.config["JWT_COOKIE_CSRF_PROTECT"] = False
        self.config["JWT_COOKIE_SAMESITE"] = "None"
        self.config["JWT_COOKIE_SECURE"] = True
        self.config["JWT_BLACKLIST_ENABLED"] = True
        self.config["JWT_ACCESS_TOKEN_EXPIRES"] = access_expires
        self.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access"]

        jwt = JWTManager(self)

        @self.after_request
        def refresh_expiring_jwt(response: Response):
            try:
                target_timestamp = datetime.timestamp(datetime.now(timezone.utc) + timedelta(hours=36))
                if target_timestamp > get_jwt()["exp"]:
                    set_access_cookies(response, create_access_token(identity=get_jwt_identity()))
                return response
            except (RuntimeError, KeyError):
                return response

        return jwt


def configure_logging(config: dict):
    dictConfig(config)


def configure_sqlalchemy(db_url: str) -> tuple[MetaData, DeclarativeMeta, Sessionmaker]:
    engine = create_engine(db_url, pool_recycle=280)  # , echo=True)
    return (db_meta := MetaData(bind=engine)), declarative_base(metadata=db_meta), Sessionmaker(bind=engine)


def configure_whooshee(sessionmaker: Sessionmaker, whoosh_base: str):
    whooshee_config = {
        "WHOOSHEE_MIN_STRING_LEN": 0,
        "WHOOSHEE_ENABLE_INDEXING": True,
        "WHOOSH_BASE": whoosh_base,
    }
    return IndexService(config=whooshee_config, session=sessionmaker())
