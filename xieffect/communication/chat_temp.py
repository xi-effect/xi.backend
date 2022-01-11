from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import User
from .chatting import ChatNamespace
from .chatting_db import UserToChat, Chat

chat_index_temp_namespace = ChatNamespace("chat-temp", path="/chat-temp/")
chat_temp_namespace = ChatNamespace("chat-temp", path="/chat-temp/<int:chat_id>/")
temp_u2c = chat_temp_namespace.model("TempU2C", UserToChat.marshal_models["temp-u2c"])


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
