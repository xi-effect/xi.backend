from datetime import datetime
from functools import wraps

from flask_restx import Resource
from flask_restx.fields import Integer
from flask_restx.reqparse import RequestParser

from common import ResponseDoc, DateTimeField, User
from .chatting_db import UserToChat, ChatRole, Chat, Message
from .chatting import ChatNamespace

messages_namespace = ChatNamespace("messages", path="/chat-temp/<int:chat_id>/messages/")

message_parser: RequestParser = RequestParser()
message_parser.add_argument("content", str, required=True)


def search_message(use_session: bool, unmoderatable: bool = True):
    def search_message_wrapper(function):
        @messages_namespace.doc_responses(ResponseDoc.error_response(403, "Not your message"))
        @messages_namespace.search_user_to_chat(None, True, True, True, True)
        @wraps(function)
        def search_message_inner(self, session, user: User, chat: Chat, user_to_chat: UserToChat, message_id: int):
            if (message := Message.find_by_ids(session, chat.id, message_id)) is None:
                return {"a": "Message not found"}, 404

            if unmoderatable or user_to_chat.role.value < ChatRole.MODER.value:
                if message.sender.id != user.id:
                    return {"a": "Not your message"}, 403

            if use_session:
                return function(self, session, message)
            return function(self, message)

        return search_message_inner

    return search_message_wrapper


@messages_namespace.route("/")
class MessageAdder(Resource):  # temp pass-through
    model = messages_namespace.model("Message", {"message_id": Integer, "sent": DateTimeField})

    @messages_namespace.doc_responses(ResponseDoc(model=model))
    @messages_namespace.search_user_to_chat(ChatRole.BASIC, True, True, True, True)
    @messages_namespace.argument_parser(message_parser)
    @messages_namespace.marshal_with(model)
    def post(self, session, user: User, chat: Chat, user_to_chat: UserToChat, content: str):
        """ For sending a new message [TEMP] """
        message = Message.create(session, chat, content, user)
        user_to_chat.activity = message.sent
        return {"message_id": message.id, "sent": message.sent}


@messages_namespace.route("/<int:message_id>/")
class MessageProcessor(Resource):  # temp pass-through
    model = messages_namespace.model("Updated Response", {"updated": DateTimeField})

    @search_message(False)
    @messages_namespace.argument_parser(message_parser)
    @messages_namespace.marshal_with(model)
    def put(self, message: Message, content: str):
        """ For editing a message (by the sender only) [TEMP] """
        message.content = content
        message.updated = datetime.utcnow()
        return {"updated": message.updated}

    @search_message(True, False)
    @messages_namespace.a_response()
    def delete(self, session, message: Message) -> None:
        """ For deleting a message (by the sender or chat moderator) [TEMP] """
        message.delete(session)
