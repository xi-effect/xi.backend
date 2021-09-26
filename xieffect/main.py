from datetime import timedelta
from json import load
from os import urandom
from random import randint
from typing import Dict

from flask import Flask
from flask_cors import CORS
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from componets.add_whoosh import IndexService

# Version control:
versions: Dict[str, str] = load(open("../files/versions.json"))

app: Flask = Flask(__name__)

# Basic config:
app.config["SECRET_KEY"] = urandom(randint(32, 64))
app.config["SECURITY_PASSWORD_SALT"] = urandom(randint(32, 64))
app.config["PROPAGATE_EXCEPTIONS"] = True

# JWT config:
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config["JWT_COOKIE_SAMESITE"] = "None"
app.config["JWT_COOKIE_SECURE"] = True
app.config["JWT_BLACKLIST_ENABLED"] = True
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=72)
app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access"]
app.config["JWT_SECRET_KEY"] = urandom(randint(32, 64))

# app.config["USE_X_SENDFILE"] = True  # breaks avatar sending
app.config["MAIL_USERNAME"] = "xieffect.edu@gmail.com"

# CORS config:
CORS(app, supports_credentials=True)  # , resources={r"/*": {"origins": "https://xieffect.vercel.app"}})

# Database config:
app.config["WHOOSHEE_MIN_STRING_LEN"] = 0
app.config["WHOOSHEE_ENABLE_INDEXING"] = True
app.config["WHOOSH_BASE"] = "../files/temp/whoosh"

engine = create_engine("sqlite:///app.db", pool_recycle=280)
db_meta = MetaData(bind=engine)
Base = declarative_base(metadata=db_meta)
Session = sessionmaker(bind=engine)

index_service = IndexService(config=app.config, session=Session())

# "mysql+mysqldb://qwert45hi:7b[-2duvd44sgoi1=pwfpji0i@qwert45hi.mysql.pythonanywhere-services.com/development"
