from flask import send_file
from flask_restx import Resource, Namespace
from flask_restx.reqparse import RequestParser

from .components import argument_parser
from setup import socketio

broadcast_namespace = Namespace("broadcast", path="/")


@broadcast_namespace.route("/test/")
class TempIndexPage(Resource):
    def get(self):
        return send_file("index.html")


@broadcast_namespace.route("/broadcast/")
class TempBroadCast(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("user_ids", int, required=True, action="append")
    parser.add_argument("data", dict, required=True)

    @argument_parser(broadcast_namespace, parser)
    def post(self, user_ids: list[int], data: dict):
        pass
        # socketio.emit()
