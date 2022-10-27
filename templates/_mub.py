from __future__ import annotations

from flask import request, send_from_directory, redirect
from flask_fullstack import counter_parser, Undefined
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import User, ResponseDoc
from moderation import MUBController, permission_index

section = permission_index.add_section("...")
permission = permission_index.add_permission(section, "...")
controller = MUBController("...")
