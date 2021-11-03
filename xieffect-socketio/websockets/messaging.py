from functools import wraps

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_socketio import join_room, leave_room, Namespace
from requests import Session
from jwt import decode

from setup import user_sessions, app


def with_chat_id(function):
    @jwt_required()
    @wraps(function)
    def with_chat_id_inner(self, data: dict):
        chat_id: int = data.get("chat-id")
        return function(self, chat_id, data)

    return with_chat_id_inner


def parse_chat_data(function):
    @with_chat_id
    @wraps(function)
    def parse_chat_data_inner(self, chat_id: int, data: dict):
        url = f"{self.host}/chats/{chat_id}/messages/"
        if (message_id := data.get("message-id", None)) is not None:
            url += f"{message_id}/"
        return function(self, url, user_sessions.sessions[get_jwt_identity()], data)

    return parse_chat_data_inner


def get_identity(jwt_cookie: str) -> int:
    jwt: str = jwt_cookie.partition("access_token_cookie=")[2].partition(";")[0]
    return decode(jwt, key=app.config["JWT_SECRET_KEY"], algorithms="HS256")["sub"]


class MessagesNamespace(Namespace):
    def __init__(self, namespace=None):
        super().__init__(namespace)
        self.host = "http://localhost:5000" if app.debug else "https://xieffect.pythonanywhere.com"

    @jwt_required()  # if not self.authenticate(request.args): raise ConnectionRefusedError("unauthorized!")
    def on_connect(self, _):
        user_sessions.connect(get_jwt_identity())

    @jwt_required()
    def on_disconnect(self):
        user_sessions.disconnect(get_jwt_identity())

    @with_chat_id
    def on_open(self, chat_id: int, _):
        join_room(f"chat-{chat_id}")

    @with_chat_id
    def on_close(self, chat_id: int, _):
        leave_room(f"chat-{chat_id}")

    @parse_chat_data
    def on_send(self, url: str, session: Session, data: dict):
        session.post(url, json=data)

    @parse_chat_data
    def on_edit(self, url: str, session: Session, data: dict):
        session.put(url, json=data)

    @parse_chat_data
    def on_delete(self, url: str, session: Session, _):
        session.delete(url)
