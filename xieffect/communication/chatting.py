from functools import wraps
from typing import Union

from flask_restx.reqparse import RequestParser

from common import Namespace, get_or_pop, ResponseDoc, User
from .chatting_db import ChatRole, UserToChat, Chat, Message


def create_403_response(has_min_role: bool) -> ResponseDoc:
    return ResponseDoc.error_response(403, "User not in chat" if has_min_role else "Chat role is lower than needed")


class ChatNamespace(Namespace):
    def search_user_to_chat(self, min_role: Union[ChatRole, None] = None, use_user_to_chat: bool = False,
                            use_chat: bool = False, use_user: bool = False, use_session: bool = False):
        def search_user_to_chat_wrapper(function):
            @self.doc_responses(create_403_response(min_role is None))
            @self.jwt_authorizer(User)
            @self.database_searcher(Chat, use_session=True)
            @wraps(function)
            def search_user_to_chat_inner(*args, **kwargs):
                session = get_or_pop(kwargs, "session", use_session)
                user = get_or_pop(kwargs, "user", use_user)
                chat = get_or_pop(kwargs, "chat", use_chat)

                if (user_to_chat := UserToChat.find_by_ids(session, chat.id, user.id)) is None:
                    return {"a": "User not in the chat"}, 403

                if min_role is not None and user_to_chat.role.value < min_role.value:
                    return {"a": f"You have to be at least chat's {min_role.to_string()}"}, 403

                if use_user_to_chat:
                    kwargs["user_to_chat"] = user_to_chat

                return function(*args, **kwargs)

            return search_user_to_chat_inner

        return search_user_to_chat_wrapper

    def manage_user(self, min_role: ChatRole):
        def manage_user_wrapper(function):
            @self.doc_responses(ResponseDoc.error_response(404, "Target user is not in the chat"))
            @self.search_user_to_chat(min_role=min_role, use_chat=True, use_user_to_chat=True)
            @self.database_searcher(User, result_field_name="target", use_session=True)
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

    def with_role_check(self):
        user_to_chat_parser: RequestParser = RequestParser()
        user_to_chat_parser.add_argument("role", str, required=True, choices=ChatRole.get_all_field_names())
        
        def with_role_check_wrapper(function):
            @self.argument_parser(user_to_chat_parser)
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

        return with_role_check_wrapper

    def search_message(self, use_session: bool, unmoderatable: bool = True):
        def search_message_wrapper(function):
            @self.doc_responses(ResponseDoc.error_response(403, "Not your message"))
            @self.search_user_to_chat(None, True, True, True, True)
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
