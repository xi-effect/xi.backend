from os import urandom
from json import load
from random import randint
from typing import Dict
from datetime import timedelta

from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Version control:
versions: Dict[str, str] = load(open("files/versions.json"))

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

app.config["USE_X_SENDFILE"] = True  # ???
app.config["MAIL_USERNAME"] = "xieffect.edu@gmail.com"

# CORS config:
CORS(app, supports_credentials=True)  # , resources={r"/*": {"origins": "https://xieffect.vercel.app"}})

# Database config:
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database/app.db"
# "mysql+mysqldb://qwert45hi:7b[-2duvd44sgoi1=pwfpji0i@qwert45hi.mysql.pythonanywhere-services.com/development"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_POOL_RECYCLE"] = 280
# app.config[""] =

db: SQLAlchemy = SQLAlchemy(app)
