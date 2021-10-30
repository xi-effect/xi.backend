from flask_restx import Resource, Model
from flask_restx.fields import Integer
from flask_restx.reqparse import RequestParser

from componets import Namespace, ResponseDoc
from users import User
from .entities import UserToChat, Chat

chat_meta_namespace = Namespace("chats", path="/chats/")

chat_meta_parser: RequestParser = RequestParser()
chat_meta_parser.add_argument("name", str, required=True)

chat_meta_view = chat_meta_namespace.model("ChatMeta", Chat.marshal_models["chat-meta"])
chat_full_view = chat_meta_namespace.model("ChatFull", Chat.marshal_models["chat-full"])


@chat_meta_namespace.route("/index/")
class ChatLister(Resource):
    @chat_meta_namespace.jwt_authorizer(User, use_session=False)
    @chat_meta_namespace.marshal_with(chat_meta_view, as_list=True, skip_none=True)
    def post(self, user: User):  # dunno how to pagination yet
        """ Get all chats with metadata """
        return user.chats


@chat_meta_namespace.route("/<int:chat_id>/")
class ChatProcessor(Resource):
    @chat_meta_namespace.jwt_authorizer(User, check_only=False)
    @chat_meta_namespace.database_searcher(Chat)
    @chat_meta_namespace.marshal_with(chat_full_view, skip_none=True)
    def get(self, chat: Chat):
        """ Returns chat's full info + user's role """
        return chat  # add user's role & user count!!!

    # @chat_meta_namespace.jwt_authorizer(User)
    # @chat_meta_namespace.database_searcher(Chat)
    # @chat_meta_namespace.argument_parser(chat_meta_parser)
    # @chat_meta_namespace.a_response()
    # def post(self, user: User, chat: Chat) -> None:
    #     """ User joins a chat [???] """
    #     pass

    @chat_meta_namespace.jwt_authorizer(User)
    @chat_meta_namespace.database_searcher(Chat, check_only=True, use_session=True)
    @chat_meta_namespace.a_response()
    def delete(self, session, chat_id: int, user: User) -> bool:
        """ Used for quitting the chat by the logged-in user. Returns `{"a": False}` if user is not in the chat """
        return UserToChat.find_and_delete(session, chat_id, user.id)


@chat_meta_namespace.route("/")
class ChatAdder(Resource):
    @chat_meta_namespace.doc_responses(ResponseDoc(model=Model("ID Response", {"id": Integer})))
    @chat_meta_namespace.jwt_authorizer(User)
    @chat_meta_namespace.argument_parser(chat_meta_parser)
    def post(self, session, name: str, user: User) -> dict[str, int]:
        """ Creates a new chat and returns its id """
        return {"id": Chat.create(session, name, user).id}


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
