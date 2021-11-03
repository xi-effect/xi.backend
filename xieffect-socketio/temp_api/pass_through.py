from flask_restx import Resource, Namespace
from flask_restx.reqparse import RequestParser

from .components import argument_parser
from websockets import room_broadcast

pass_through_namespace = Namespace("passthrough", path="/pass-through/")


@pass_through_namespace.route("/")
class Temp(Resource):
    parser = RequestParser()
    parser.add_argument("chat-id", int, required=True, dest="chat_id")
    parser.add_argument("event", str, required=True)
    parser.add_argument("data", dict, required=True)

    @argument_parser(pass_through_namespace, parser)
    def post(self, chat_id: int, event: str, data: dict):
        for user_id, unread in data.items():
            room_broadcast(event, {"chat-id": chat_id, "unread": unread}, f"user-{user_id}")
