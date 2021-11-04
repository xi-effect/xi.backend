from flask_restx import Resource, Namespace
from flask_restx.reqparse import RequestParser

from .components import argument_parser
from websockets import room_broadcast

pass_through_namespace = Namespace("passthrough", path="/pass-through/")


@pass_through_namespace.route("/")
class Temp(Resource):
    parser = RequestParser()
    parser.add_argument("event", str, required=True)
    parser.add_argument("data", dict, required=True)
    parser.add_argument("user-ids", int, required=False, action="append", dect="user_ids")
    parser.add_argument("user-data", dict, required=False, dect="user_data")

    @argument_parser(pass_through_namespace, parser)
    def post(self, event: str, data: dict, user_ids: list[int], user_data: dict):
        if user_data is not None:
            for user_id, event_data in user_data.items():
                event_data.update(data)
                room_broadcast(event, event_data, f"user-{user_id}")
        else:
            for user_id in user_ids:
                room_broadcast(event, data, f"user-{user_id}")
