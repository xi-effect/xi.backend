from flask_restx import Resource, Namespace
from flask_restx.reqparse import RequestParser

from .components import argument_parser
from setup import socketio, storage

broadcast_namespace = Namespace("broadcast", path="/broadcast/")


@broadcast_namespace.route("/")
class TempBroadCast(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("user_ids", int, required=True, action="append")
    parser.add_argument("data", dict, required=True)

    @argument_parser(broadcast_namespace, parser)
    def post(self, user_ids: list[int], data: dict):
        pass
        # socketio.emit()
