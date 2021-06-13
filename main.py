from os import urandom
from random import randint
from typing import Dict
from datetime import timedelta

from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Version control:
versions: Dict[str, str] = {
    "API": "0.7.5i",  # relates to everything in api_resources package
    "DBK": "0.6.3",  # relates to everything in database package
    "CAT": "0.3.5",  # relates to /cat/.../ resources
    "OCT": "0.2.8",  # relates to side thing (olympiad checker)
    "XiE": "-",  # relates to XiE webapp version (out of this project)
}

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

# # Mail config:
# app.config["MAIL_SERVER"] = "smtp.gmail.com"
# app.config["MAIL_PORT"] = 587
# app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "xieffect.edu@gmail.com"
# app.config["MAIL_PASSWORD"] = "6848048Igor"
# app.config["MAIL_DEFAULT_SENDER"] = "xieffect.edu@gmail.com"

# mail: Mail = Mail(app)

# CORS config:
CORS(app, supports_credentials=True)  # , resources={r"/*": {"origins": "https://xieffect.vercel.app"}})

# Database config:
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database/app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# app.config[""] =

db: SQLAlchemy = SQLAlchemy(app)
