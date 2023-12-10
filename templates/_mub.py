from __future__ import annotations

from flask import request, send_from_directory, redirect
from flask_fullstack import counter_parser, Undefined, RequestParser
from flask_restx import Resource

from common import ResponseDoc
from moderation import MUBController, permission_index
from users.users_db import User

section = permission_index.add_section("...")
permission = permission_index.add_permission(section, "...")
controller = MUBController("...")
