from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import Namespace, counter_parser
from users import User
from .entities import UserToChat, ChatRole, Chat, Message

messages_namespace = Namespace("messages", path="/chats/<int:chat_id>/messages/")

message_parser: RequestParser = RequestParser()
message_parser.add_argument("content", str, required=True)

message_view = messages_namespace.model("Message", Message.marshal_models["message-full"])


@messages_namespace.route("/")
class MessageAdder(Resource):  # temp pass-through
    @messages_namespace.a_response()
    @messages_namespace.jwt_authorizer(User)
    @messages_namespace.database_searcher(Chat)
    @messages_namespace.argument_parser(message_parser)
    def post(self, user: User, chat: Chat, content: str) -> None:
        """ For sending a new message [TEMP] """
        pass


@messages_namespace.route("/history/")
class MessageLister(Resource):
    @messages_namespace.jwt_authorizer(User)
    @messages_namespace.database_searcher(Chat)
    @messages_namespace.argument_parser(counter_parser)
    @messages_namespace.lister(50, message_view)
    def post(self, user: User, chat: Chat, start: int, finish: int) -> list[Message]:
        """ Lists chat's messages (new on top) """
        pass


@messages_namespace.route("/<int:message_id>/")
class MessageManager(Resource):
    @messages_namespace.a_response()
    @messages_namespace.jwt_authorizer(User)
    @messages_namespace.database_searcher(Chat, check_only=True)
    @messages_namespace.argument_parser(message_parser)
    def put(self, user: User, chat_id: int, message_id: int) -> None:
        """ For editing a message (by the sender only) """
        pass

    @messages_namespace.a_response()
    @messages_namespace.jwt_authorizer(User)
    @messages_namespace.database_searcher(Chat, check_only=True)
    def delete(self, user: User, chat_id: int, message_id: int) -> None:
        """ For deleting a message (by sender or chat moder) """
        pass
