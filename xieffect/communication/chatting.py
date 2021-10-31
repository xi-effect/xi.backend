from functools import wraps

from flask_restx import Resource, Model
from flask_restx.fields import Integer
from flask_restx.reqparse import RequestParser

from componets import counter_parser, ResponseDoc
from users import User
from .entities import UserToChat, Chat, Message, ChatRole
from .helpers import ChatNamespace

chats_namespace = ChatNamespace("chats", path="/chats/")

chat_meta_parser: RequestParser = RequestParser()
chat_meta_parser.add_argument("name", str, required=True)

user_to_chat_parser: RequestParser = RequestParser()
user_to_chat_parser.add_argument("role", str, required=True, choices=ChatRole.get_all_field_names())

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


@chats_namespace.route("/")
class ChatAdder(Resource):
    @chats_namespace.doc_responses(ResponseDoc(model=Model("ID Response", {"id": Integer})))
    @chats_namespace.jwt_authorizer(User)
    @chats_namespace.argument_parser(chat_meta_parser)
    def post(self, session, name: str, user: User) -> dict[str, int]:
        """ Creates a new chat and returns its id """
        return {"id": Chat.create(session, name, user).id}


@chats_namespace.route("/<int:chat_id>/")
class ChatProcessor(Resource):
    @chats_namespace.search_user_to_chat(use_user_to_chat=True)
    @chats_namespace.marshal_with(chat_full_view, skip_none=True)
    def get(self, user_to_chat: UserToChat):
        """ Returns chat's full info + user's role """
        return user_to_chat

    # @chats_namespace.jwt_authorizer(User)
    # @chats_namespace.database_searcher(Chat)
    # @chats_namespace.argument_parser(chat_meta_parser)
    # @chats_namespace.a_response()
    # def post(self, user: User, chat: Chat) -> None:
    #     """ User joins a chat [???] """
    #     pass

    @chats_namespace.search_user_to_chat(use_user_to_chat=True, use_session=True)
    @chats_namespace.a_response()
    def delete(self, session, user_to_chat: UserToChat) -> None:
        """ Used for quitting the chat by the logged-in user """
        user_to_chat.delete(session)


@chats_namespace.route("/<int:chat_id>/users/")
class ChatUserLister(Resource):
    @chats_namespace.search_user_to_chat(use_chat=True)
    @chats_namespace.argument_parser(counter_parser)
    @chats_namespace.lister(50, chat_user_view)
    def post(self, chat: Chat, start: int, finish: int) -> list[UserToChat]:
        return chat.participants[start:finish + 1]


@chats_namespace.route("/<int:chat_id>/message-history/")
class MessageLister(Resource):
    @chats_namespace.search_user_to_chat(use_chat=True)
    @chats_namespace.argument_parser(counter_parser)
    @chats_namespace.lister(50, message_view)
    def post(self, chat: Chat, start: int, finish: int) -> list[Message]:
        """ Lists chat's messages (new on top) """
        return chat.messages[start:finish + 1]


@chats_namespace.route("/<int:chat_id>/manage/")
class ChatManager(Resource):
    @chats_namespace.search_user_to_chat(min_role=ChatRole.ADMIN, use_chat=True)
    @chats_namespace.argument_parser(chat_meta_parser)
    @chats_namespace.a_response()
    def put(self, chat: Chat, name: str) -> None:
        """ Changes some of chat's metadata (chat admins only) """
        chat.name = name

    @chats_namespace.search_user_to_chat(min_role=ChatRole.OWNER, use_chat=True, use_session=True)
    @chats_namespace.a_response()
    def delete(self, session, chat: Chat) -> None:
        """ Deletes a chat (chat owner only) """
        chat.delete(session)


def manage_user(with_role: bool = False):
    def manage_user_wrapper(function):
        @chats_namespace.doc_responses(ResponseDoc.error_response(404, "Target user is not in the chat"))
        @chats_namespace.search_user_to_chat(min_role=ChatRole.ADMIN, use_chat=True, use_user_to_chat=True)
        @chats_namespace.database_searcher(User, result_field_name="target", use_session=True)
        @wraps(function)
        def manage_user_inner(session, user_to_chat: UserToChat, chat: Chat, target: User):
            target_to_chat: UserToChat = UserToChat.find_by_ids(session, chat.id, target.id)
            if target_to_chat is None:
                return {"a": "Target user is not in the chat"}, 404

            if with_role:
                return function(session, target_to_chat)
            return function(user_to_chat, target_to_chat)

        return manage_user_inner

    return manage_user_wrapper


def with_role_check(function):
    @manage_user(with_role=True)
    @chats_namespace.argument_parser(user_to_chat_parser)
    @wraps(function)
    def with_role_check_inner(user_to_chat: UserToChat, target_to_chat: UserToChat, role: str):
        try:
            role: ChatRole = ChatRole.from_string(role)
        except (ValueError, KeyError):
            return {"a": f"Chat role '{role}' is not supported"}, 400  # redo!

        if role.value >= user_to_chat.role.value:
            return {"a": "You can only set roles below your own"}, 403

        return function(target_to_chat, role)

    return with_role_check_inner


@chats_namespace.route("/<int:chat_id>/users/<int:user_id>/")
class ChatUserManager(Resource):
    @chats_namespace.search_user_to_chat(min_role=ChatRole.ADMIN, use_chat=True)
    @chats_namespace.database_searcher(User, result_field_name="target")
    @chats_namespace.a_response()
    def post(self, chat: Chat, target: User) -> None:
        """ Adds (invites?) a user to the chat """
        chat.add_participant(target)

    @with_role_check
    @chats_namespace.a_response()
    def put(self, target_to_chat: UserToChat, role: ChatRole) -> None:
        """ Changes user's role """
        target_to_chat.role = role

    @manage_user()
    @chats_namespace.a_response()
    def delete(self, session, target_to_chat: UserToChat) -> None:
        """ Removes a user from the chat """
        target_to_chat.delete(session)


@chats_namespace.route("/<int:chat_id>/users/add-all/")
class ChatUserManager(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("ids", type=list, required=True)

    @chats_namespace.search_user_to_chat(min_role=ChatRole.ADMIN, use_session=True, use_chat=True)
    @chats_namespace.argument_parser(parser)
    @chats_namespace.a_response()
    def post(self, session, chat: Chat, ids: list[int]) -> None:
        """ Adds (invites?) a list of users by ids to the chat """
        for user_id in ids:
            user: User = User.find_by_id(session, user_id)
            if user is not None and UserToChat.find_by_ids(session, chat.id, user_id) is None:
                chat.add_participant(user)  # no error check, REDO
