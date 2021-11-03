from flask_restx import Resource, Namespace
from flask_restx.reqparse import RequestParser

from .components import argument_parser
from websockets import room_broadcast

pass_through_namespace = Namespace("passthrough", path="/pass-through/")


@pass_through_namespace.route("/broadcast/<event>/")
class TempBroadcast(Resource):
    parser = RequestParser()
    parser.add_argument("data", dict, required=True)
    parser.add_argument("user_ids", int, required=True, action="append")

    @argument_parser(pass_through_namespace, parser)
    def post(self, event: str, data: dict, user_ids: list[int]):
        for user_id in user_ids:
            room_broadcast(event, data, f"user-{user_id}")
