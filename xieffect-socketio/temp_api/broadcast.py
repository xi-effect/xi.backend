from flask_restx import Resource, Namespace
from flask_restx.reqparse import RequestParser

from .components import argument_parser
from setup import socketio, storage

broadcast_namespace = Namespace("broadcast", path="/broadcast/")
data_parser = RequestParser()
data_parser.add_argument("data", dict, required=True)


def broadcast(event: str, data: dict, *user_ids: int):
    for user_id in user_ids:
        if (session_id := storage.get(user_id, None)) is not None:
            socketio.emit(event, data, to=session_id)


def room_broadcast(event: str, data: dict, room: str, namespace: str = "/"):
    socketio.emit(event, data, to=room, namespace=namespace)


@broadcast_namespace.route("/<event>/")
class TempBroadCast(Resource):
    parser: RequestParser = data_parser.copy()
    parser.add_argument("user_ids", int, required=True, action="append")

    @argument_parser(broadcast_namespace, parser)
    def post(self, event: str, data: dict, user_ids: list[int]):
        broadcast(event, data, *user_ids)


@broadcast_namespace.route("/<event>/rooms/<room>/")
class TempBroadCast(Resource):
    @argument_parser(broadcast_namespace, data_parser)
    def post(self, event: str, room: str, data: dict):
        room_broadcast(event, data, room)
