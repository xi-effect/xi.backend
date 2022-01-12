from flask_restx import Resource

from common import counter_parser, User
from .chatting_db import UserToChat, Chat, Message
from .chatting import ChatNamespace

chats_namespace = ChatNamespace("chats", path="/chats/")

chat_index_view = chats_namespace.model("ChatIndex", UserToChat.marshal_models["chat-user-index"])
chat_full_view = chats_namespace.model("ChatFull", UserToChat.marshal_models["chat-user-full"])
chat_user_view = chats_namespace.model("ChatUser", UserToChat.marshal_models["user-in-chat"])

message_view = chats_namespace.model("Message", Message.marshal_models["message"])


@chats_namespace.route("/index/")
class ChatLister(Resource):
    @chats_namespace.jwt_authorizer(User)
    @chats_namespace.argument_parser(counter_parser)
    @chats_namespace.lister(50, chat_index_view)
    def post(self, session, user: User, start: int, finish: int):  # dunno how to pagination yet
        """ Get all chats with metadata """
        return UserToChat.find_by_user(session, user.id, start, finish - start)


@chats_namespace.route("/<int:chat_id>/")
class ChatProcessor(Resource):
    @chats_namespace.search_user_to_chat(use_user_to_chat=True)
    @chats_namespace.marshal_with(chat_full_view, skip_none=True)
    def get(self, user_to_chat: UserToChat):
        """ Returns chat's full info + user's role """
        return user_to_chat


@chats_namespace.route("/<int:chat_id>/users/")
class ChatUserLister(Resource):
    @chats_namespace.search_user_to_chat(use_chat=True)
    @chats_namespace.argument_parser(counter_parser)
    @chats_namespace.lister(50, chat_user_view)
    def post(self, chat: Chat, start: int, finish: int) -> list[UserToChat]:
        return chat.participants[start:finish]


@chats_namespace.route("/<int:chat_id>/message-history/")
class MessageLister(Resource):
    @chats_namespace.search_user_to_chat(use_chat=True)
    @chats_namespace.argument_parser(counter_parser)
    @chats_namespace.lister(50, message_view)
    def post(self, chat: Chat, start: int, finish: int) -> list[Message]:
        """ Lists chat's messages (new on top) """
        return chat.messages[start:finish]
