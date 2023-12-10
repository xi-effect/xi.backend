from __future__ import annotations

from flask import request, send_from_directory, redirect
from flask_fullstack import counter_parser, Undefined, RequestParser
from flask_restx import Resource

from common import ResourceController, ResponseDoc
from users.users_db import User

controller = ResourceController("...")
