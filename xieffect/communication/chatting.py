from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import Namespace, counter_parser
from users import User
from .entities import UserToChat, ChatRole, Chat

chat_meta_namespace = Namespace("chats", path="/chats/")

chat_meta_parser: RequestParser = RequestParser()
chat_meta_parser.add_argument("name", str, required=True)

chat_meta_view = chat_meta_namespace.model("ChatMeta", Chat.marshal_models["chat-meta"])
chat_full_view = chat_meta_namespace.model("ChatFull", Chat.marshal_models["chat-full"])


@chat_meta_namespace.route("/index/")
class ChatLister(Resource):
    @chat_meta_namespace.jwt_authorizer(User)
    @chat_meta_namespace.marshal_with(chat_meta_view, as_list=True, skip_none=True)
    def post(self, session, user: User):  # dunno how to pagination yet
        """ Get all chats with metadata """
        pass


@chat_meta_namespace.route("/<int:chat_id>/")
class ChatProcessor(Resource):
    @chat_meta_namespace.jwt_authorizer(User)
    @chat_meta_namespace.database_searcher(Chat, use_session=True)
    @chat_meta_namespace.marshal_with(chat_full_view, skip_none=True)
    def get(self, session, user: User, chat: Chat):
        """ Returns chat's full info """
        pass

    @chat_meta_namespace.a_response()
    @chat_meta_namespace.jwt_authorizer(User)
    @chat_meta_namespace.database_searcher(Chat, use_session=True)
    @chat_meta_namespace.argument_parser(chat_meta_parser)
    def post(self, session, user: User, chat: Chat) -> None:
        """ User joins a chat [???] """
        pass

    @chat_meta_namespace.a_response()
    @chat_meta_namespace.jwt_authorizer(User)
    @chat_meta_namespace.database_searcher(Chat, use_session=True)
    def delete(self, session, user: User, chat: Chat) -> None:
        """ Used for quitting the chat by the logged-in user """
        pass


@chat_meta_namespace.route("/")
class ChatAdder(Resource):
    @chat_meta_namespace.a_response()
    @chat_meta_namespace.jwt_authorizer(User)
    @chat_meta_namespace.argument_parser(chat_meta_parser)
    def post(self, session, user: User, name: str) -> None:
        """ Creates a new chat """
        pass


@chat_meta_namespace.route("/<int:chat_id>/manage/")
class ChatManager(Resource):
    @chat_meta_namespace.a_response()
    @chat_meta_namespace.jwt_authorizer(User)
    @chat_meta_namespace.database_searcher(Chat, use_session=True)
    @chat_meta_namespace.argument_parser(chat_meta_parser)
    def put(self, session, user: User, chat: Chat) -> None:
        """ Changes some of chat's metadata (chat admins only) """
        pass

    @chat_meta_namespace.a_response()
    @chat_meta_namespace.jwt_authorizer(User)
    @chat_meta_namespace.database_searcher(Chat, use_session=True)
    def delete(self, session, user: User, chat: Chat) -> None:
        """ Deletes a chat (chat admins only) """
        pass


@chat_meta_namespace.route("/<int:chat_id>/users/<int:user_id>/")
class ChatUserManager(Resource):
    @chat_meta_namespace.a_response()
    @chat_meta_namespace.jwt_authorizer(User)
    @chat_meta_namespace.database_searcher(User, result_field_name="target")
    @chat_meta_namespace.database_searcher(Chat, use_session=True)
    def post(self, session, user: User, chat: Chat, target: User) -> None:
        """ Adds (invites?) a user to the chat """
        pass

    @chat_meta_namespace.a_response()
    @chat_meta_namespace.jwt_authorizer(User)
    @chat_meta_namespace.database_searcher(User, result_field_name="target")
    @chat_meta_namespace.database_searcher(Chat, use_session=True)
    def put(self, session, user: User, chat: Chat, target: User) -> None:
        """ Changes user's role """
        pass

    @chat_meta_namespace.a_response()
    @chat_meta_namespace.jwt_authorizer(User)
    @chat_meta_namespace.database_searcher(User, result_field_name="target")
    @chat_meta_namespace.database_searcher(Chat, use_session=True)
    def delete(self, session, user: User, chat: Chat, target: User) -> None:
        """ Removes a user from the chat """
        pass
