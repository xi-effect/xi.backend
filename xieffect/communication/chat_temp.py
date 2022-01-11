from functools import wraps
from typing import Union

from flask_restx import Resource, Model
from flask_restx.fields import Integer
from flask_restx.reqparse import RequestParser

from common import ResponseDoc, User
from .entities import UserToChat, Chat, ChatRole
from .helpers import ChatNamespace

chat_index_temp_namespace = ChatNamespace("chat-temp", path="/chat-temp/")
chat_temp_namespace = ChatNamespace("chat-temp", path="/chat-temp/<int:chat_id>/")
temp_u2c = chat_temp_namespace.model("TempU2C", UserToChat.marshal_models["temp-u2c"])

chat_meta_parser: RequestParser = RequestParser()
chat_meta_parser.add_argument("name", str, required=True)

user_to_chat_parser: RequestParser = RequestParser()
user_to_chat_parser.add_argument("role", str, required=True, choices=ChatRole.get_all_field_names())


@chat_index_temp_namespace.route("/")
class ChatAdder(Resource):
    @chat_index_temp_namespace.doc_responses(ResponseDoc(model=Model("ID Response", {"id": Integer})))
    @chat_index_temp_namespace.jwt_authorizer(User)
    @chat_index_temp_namespace.argument_parser(chat_meta_parser)
    def post(self, session, name: str, user: User) -> dict[str, int]:
        """ Creates a new chat and returns its id """
        return {"id": Chat.create(session, name, user).id}


@chat_index_temp_namespace.route("/close-all/")
class ChatCloser(Resource):  # temp pass-through
    parser: RequestParser = RequestParser()
    parser.add_argument("ids", type=int, action="append", required=True)

    @chat_index_temp_namespace.jwt_authorizer(User)
    @chat_index_temp_namespace.argument_parser(parser)
    @chat_index_temp_namespace.a_response()
    def post(self, session, user: User, ids: list[int]) -> None:
        """ Sets all in-chat statuses to offline (for chats form the list in parameters) [TEMP] """
        UserToChat.find_and_close(session, user.id, ids)


@chat_temp_namespace.route("/users/all/")
class ChatFullUserLister(Resource):  # temp pass-through
    @chat_temp_namespace.jwt_authorizer(User, check_only=True, use_session=False)
    @chat_temp_namespace.database_searcher(Chat)
    @chat_temp_namespace.response(200, "A list of user ids")
    def get(self, chat: Chat) -> list[UserToChat]:
        return [u2c.user_id for u2c in chat.participants]


@chat_temp_namespace.route("/users/offline/")
class ChatOfflineUserLister(Resource):  # temp pass-through
    @chat_temp_namespace.jwt_authorizer(User, check_only=True, use_session=False)
    @chat_temp_namespace.database_searcher(Chat, use_session=True)
    @chat_temp_namespace.marshal_list_with(temp_u2c)
    def get(self, session, chat: Chat) -> list[UserToChat]:
        return UserToChat.find_by_chat(session, chat.id)


@chat_temp_namespace.route("/presence/")
class MessageReader(Resource):  # temp pass-through
    parser: RequestParser = RequestParser()
    parser.add_argument("online", type=bool)

    @chat_temp_namespace.search_user_to_chat(use_user_to_chat=True)
    @chat_temp_namespace.argument_parser(parser)
    @chat_temp_namespace.a_response()
    def post(self, user_to_chat: UserToChat, online: bool) -> bool:
        """ Sets if the user has this chat open & returns if notif event is needed [TEMP] """
        user_to_chat.online += 1 if online else -1
        if online and user_to_chat.online == 1 and user_to_chat.unread != 0:
            user_to_chat.unread = 0
            return True
        return False


@chat_temp_namespace.route("/membership/")
class ChatProcessor(Resource):  # temp pass-through
    # @chat_temp_namespace.jwt_authorizer(User)
    # @chat_temp_namespace.database_searcher(Chat)
    # @chat_temp_namespace.argument_parser(chat_meta_parser)
    # @chat_temp_namespace.a_response()
    # def post(self, user: User, chat: Chat) -> None:  # redo as event
    #     """ User joins a chat [???] """
    #     pass

    @chat_temp_namespace.search_user_to_chat(use_user_to_chat=True, use_session=True)
    def delete(self, session, user_to_chat: UserToChat):  # redo as event
        """ Used for quitting the chat by the logged-in user [TEMP] """
        user_to_chat.delete(session)
        if user_to_chat.role is ChatRole.OWNER:  # Automatic ownership transfer
            if (successor := UserToChat.find_successor(session, user_to_chat.chat_id)) is None:
                Chat.find_by_id(session, user_to_chat.chat_id).delete(session)
                return {"branch": "delete-chat"}
            successor.role = ChatRole.OWNER
            return {"branch": "assign-owner", "successor": successor.user_id}
        return {"branch": "just-quit"}


@chat_temp_namespace.route("/manage/")
class ChatManager(Resource):  # temp pass-through
    @chat_temp_namespace.search_user_to_chat(min_role=ChatRole.ADMIN, use_chat=True)
    @chat_temp_namespace.argument_parser(chat_meta_parser)
    @chat_temp_namespace.a_response()
    def put(self, chat: Chat, name: str) -> None:  # redo as event
        """ Changes some of chat's metadata (chat admins only) [TEMP] """
        chat.name = name
        # pass_through("edit-chat", {"chat-id": chat.id, "name": name}, [u2c.user_id for u2c in chat.participants])

    @chat_temp_namespace.search_user_to_chat(min_role=ChatRole.OWNER, use_chat=True, use_session=True)
    @chat_temp_namespace.a_response()
    def delete(self, session, chat: Chat) -> None:  # redo as event
        """ Deletes a chat (chat owner only) [TEMP] """
        # user_ids = [u2c.user_id for u2c in chat.participants]
        chat.delete(session)
        # pass_through("delete-chat", {"chat-id": chat.id}, user_ids)


def manage_user(min_role: ChatRole):
    def manage_user_wrapper(function):
        @chat_temp_namespace.doc_responses(ResponseDoc.error_response(404, "Target user is not in the chat"))
        @chat_temp_namespace.search_user_to_chat(min_role=min_role, use_chat=True, use_user_to_chat=True)
        @chat_temp_namespace.database_searcher(User, result_field_name="target", use_session=True)
        @wraps(function)
        def manage_user_inner(*args, session, user_to_chat: UserToChat, chat: Chat, target: User):
            target_to_chat: UserToChat = UserToChat.find_by_ids(session, chat.id, target.id)
            if target_to_chat is None:
                return {"a": "Target user is not in the chat"}, 404

            if target_to_chat.role.value >= user_to_chat.role.value:
                return {"a": "Your role is not higher that user's"}, 403

            if min_role is ChatRole.MODER or min_role is ChatRole.OWNER:
                return function(user_to_chat=user_to_chat, target_to_chat=target_to_chat, *args)
            return function(session=session, target_to_chat=target_to_chat, *args)

        return manage_user_inner

    return manage_user_wrapper


def with_role_check(function):
    @chat_temp_namespace.argument_parser(user_to_chat_parser)
    @wraps(function)
    def with_role_check_inner(*args, user_to_chat: UserToChat, role: Union[str, None] = None,
                              target_to_chat: Union[UserToChat, None] = None, **kwargs):
        try:
            role: ChatRole = ChatRole.BASIC if role is None else ChatRole.from_string(role)
        except (ValueError, KeyError):
            return {"a": f"Chat role '{role}' is not supported"}, 400  # redo!

        if role.value >= user_to_chat.role.value:
            return {"a": "You can only set roles below your own"}, 403

        if target_to_chat is None:
            return function(role=role, *args, **kwargs)
        return function(target_to_chat=target_to_chat, role=role, *args, **kwargs)

    return with_role_check_inner


@chat_temp_namespace.route("/users/<int:user_id>/owner/")
class OwnershipTransfer(Resource):
    @manage_user(ChatRole.OWNER)
    @chat_temp_namespace.a_response()
    def post(self, user_to_chat: UserToChat, target_to_chat: UserToChat) -> None:
        """ Ownership transfer [TEMP] """
        user_to_chat.role = ChatRole.ADMIN
        target_to_chat.role = ChatRole.OWNER


@chat_temp_namespace.route("/users/<int:user_id>/")
class ChatUserManager(Resource):  # temp pass-through
    @chat_temp_namespace.search_user_to_chat(ChatRole.ADMIN, True, True, False, True)
    @with_role_check
    @chat_temp_namespace.a_response()
    def post(self, session, chat: Chat, user_id: int, role: ChatRole) -> bool:  # redo as event
        """ Adds a user to the chat (admins only) [TEMP] """
        return chat.add_participant(session, User.find_by_id(session, user_id), role)

    @manage_user(ChatRole.MODER)
    @with_role_check
    @chat_temp_namespace.a_response()
    def put(self, target_to_chat: UserToChat, role: ChatRole) -> bool:  # redo as event
        """ Changes user's role (admins only) [TEMP] """
        if target_to_chat.role == role:
            return False
        target_to_chat.role = role
        return True

    @manage_user(ChatRole.ADMIN)
    @chat_temp_namespace.a_response()
    def delete(self, session, target_to_chat: UserToChat) -> None:  # redo as event
        """ Removes a user from the chat (admins only) [TEMP] """
        target_to_chat.delete(session)


@chat_temp_namespace.route("/users/add-all/")
class ChatUserBulkAdder(Resource):  # temp pass-through
    parser: RequestParser = RequestParser()
    parser.add_argument("ids", type=int, required=True, action="append")

    @chat_temp_namespace.search_user_to_chat(min_role=ChatRole.ADMIN, use_session=True, use_chat=True)
    @chat_temp_namespace.argument_parser(parser)
    def post(self, session, chat: Chat, ids: list[int]) -> list[bool]:  # redo as event
        """ Adds a list of users by ids to the chat (admins only) [TEMP] """
        return [(user := User.find_by_id(session, user_id)) is not None
                and chat.add_participant(session, user)
                for user_id in ids]
