from functools import wraps
from typing import Optional

from componets import Namespace, get_or_pop, ResponseDoc, message_response
from users import User
from .entities import ChatRole, UserToChat, Chat


class ChatNamespace(Namespace):
    def search_user_to_chat(self, min_role: Optional[ChatRole] = None, use_user_to_chat: bool = False,
                            use_chat: bool = False, use_user: bool = False, use_session: bool = False):
        def search_user_to_chat_wrapper(function):
            message_response.register_model(self)

            @wraps(function)
            @self.doc_responses(ResponseDoc(403, "User doesn't have needed role in the chat", message_response.model))
            @self.jwt_authorizer(User)
            @self.database_searcher(Chat, use_session=True)
            def search_user_to_chat_inner(*args, **kwargs):
                session = get_or_pop(kwargs, "session", use_session)
                user = get_or_pop(kwargs, "user", use_user)
                chat = get_or_pop(kwargs, "chat", use_chat)

                if (user_to_chat := UserToChat.find_by_ids(session, chat.id, user.id)) is None:
                    return {"a": "User not in the chat"}, 403

                if min_role is not None and user_to_chat.role < min_role:
                    return {"a": f"You have to be at least chat's {min_role.to_string()}"}, 403

                if use_user_to_chat:
                    kwargs["user_to_chat"] = use_user_to_chat

                return function(*args, **kwargs)

            return search_user_to_chat_inner

        return search_user_to_chat_wrapper
