from datetime import timedelta
from json import load
from logging.config import dictConfig
from os import getenv
from typing import Dict

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from common._whoosh import IndexService  # noqa

dictConfig({
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

load_dotenv("../.env")

# Version control:
versions: Dict[str, str] = load(open("../files/versions.json", encoding="utf-8"))

app: Flask = Flask(__name__)

# Basic config:
app.config["PROPAGATE_EXCEPTIONS"] = True
# app.config["USE_X_SENDFILE"] = True  # breaks avatar sending
app.config["MAIL_USERNAME"] = "xieffect.edu@gmail.com"

# JWT config:
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config["JWT_COOKIE_SAMESITE"] = "None"
app.config["JWT_COOKIE_SECURE"] = True
app.config["JWT_BLACKLIST_ENABLED"] = True
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=72)
app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access"]

# Secret config:
for secret_name in ["SECRET_KEY", "SECURITY_PASSWORD_SALT", "JWT_SECRET_KEY", "API_KEY"]:
    app.config[secret_name] = getenv(secret_name, "hope it's local")

# CORS config:
CORS(app, supports_credentials=True)

# Database config:
app.config["WHOOSHEE_MIN_STRING_LEN"] = 0
app.config["WHOOSHEE_ENABLE_INDEXING"] = True
app.config["WHOOSH_BASE"] = "../files/temp/whoosh"

engine = create_engine("sqlite:///app.db", pool_recycle=280)  # , echo=True)
db_meta = MetaData(bind=engine)
Base = declarative_base(metadata=db_meta)
Session = sessionmaker(bind=engine)

index_service = IndexService(config=app.config, session=Session())

# "mysql+mysqldb://qwert45hi:7b[-2duvd44sgoi1=pwfpji0i@qwert45hi.mysql.pythonanywhere-services.com/development"
