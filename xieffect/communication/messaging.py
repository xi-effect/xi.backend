from datetime import datetime
from functools import wraps

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import ResponseDoc
from users import User
from .entities import UserToChat, ChatRole, Chat, Message
from .helpers import ChatNamespace

messages_namespace = ChatNamespace("messages", path="/chats/<int:chat_id>/messages/")

message_parser: RequestParser = RequestParser()
message_parser.add_argument("content", str, required=True)


def search_message(use_session: bool, unmoderatable: bool = True):
    def search_message_wrapper(function):
        @messages_namespace.doc_responses(ResponseDoc.error_response(403, "Not your message"))
        @messages_namespace.search_user_to_chat(use_user=True, use_chat=True, use_user_to_chat=True)
        @wraps(function)
        def search_message_inner(session, user: User, chat: Chat, user_to_chat: UserToChat, message_id: int):
            if (message := Message.find_by_ids(session, chat.id, message_id)) is None:
                return {"a": "Message not found"}, 404

            if unmoderatable or user_to_chat.role < ChatRole.MODER:
                if message.sender.id != user.id:
                    return {"a": "Not your message"}, 403

            if use_session:
                return function(session, message)
            return function(message)

        return search_message_inner

    return search_message_wrapper


@messages_namespace.route("/")
class MessageAdder(Resource):  # temp pass-through
    @messages_namespace.search_user_to_chat(min_role=ChatRole.BASIC, use_chat=True, use_user=True, use_session=True)
    @messages_namespace.argument_parser(message_parser)
    @messages_namespace.a_response()
    def post(self, session, user: User, chat: Chat, content: str) -> None:
        """ For sending a new message [TEMP] """
        Message.create(session, chat, content, user)


@messages_namespace.route("/<int:message_id>/")
class MessageProcessor(Resource):  # temp pass-through
    @search_message(False)
    @messages_namespace.argument_parser(message_parser)
    @messages_namespace.a_response()
    def put(self, message: Message, content: str) -> None:
        """ For editing a message (by the sender only) [TEMP] """
        message.content = content
        message.updated = datetime.utcnow()

    @search_message(True, False)
    @messages_namespace.a_response()
    def delete(self, session, message: Message) -> None:
        """ For deleting a message (by the sender or chat moderator) [TEMP] """
        message.delete(session)
