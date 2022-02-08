from os import getenv

from flask_jwt_extended import JWTManager

from __lib__.flask_fullstack import Flask as _Flask, configure_logging, configure_whooshee, configure_sqlalchemy


class Flask(_Flask):
    def configure_jwt_manager(self, *args, **kwargs) -> JWTManager:
        from .users_db import TokenBlockList
        jwt = super().configure_jwt_manager(*args, **kwargs)

        @jwt.token_in_blocklist_loader
        @sessionmaker.with_begin
        def check_if_token_revoked(_, jwt_payload, session):
            return TokenBlockList.find_by_jti(session, jwt_payload["jti"]) is not None

        return jwt


def init_xieffect():  # xieffect specific:
    from dotenv import load_dotenv
    from json import load

    load_dotenv("../.env")

    db_url: str = getenv("DB_LINK", "sqlite:///app.db")
    db_meta, Base, sessionmaker = configure_sqlalchemy(db_url)
    index_service = configure_whooshee(sessionmaker, "../files/temp/whoosh")
    configure_logging({
        "version": 1,
        "formatters": {"default": {
            "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        }},
        "handlers": {"wsgi": {
            "class": "logging.StreamHandler",
            "stream": "ext://flask.logging.wsgi_errors_stream",
            "formatter": "default"
        }},
        "root": {
            "level": "DEBUG",
            "handlers": ["wsgi"]
        }
    })

    versions = load(open("../files/versions.json", encoding="utf-8"))

    app: Flask = Flask(__name__, static_folder="../files/static", static_url_path="/static/", versions=versions)
    app.secrets_from_env("hope it's local")  # TODO DI to use secrets in `URLSafeSerializer`s
    app.configure_cors()

    return db_url, db_meta, Base, sessionmaker, index_service, versions, app


db_url, db_meta, Base, sessionmaker, index_service, versions, app = init_xieffect()
