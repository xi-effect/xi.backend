from functools import wraps

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_socketio import join_room, leave_room, Namespace
from requests import Session
from jwt import decode

from setup import user_sessions, app
from .broadcast import room_broadcast


def parse_chat_data(function):
    @jwt_required()
    @wraps(function)
    def parse_chat_data_inner(self, data: dict):
        chat_id: int = data.get("chat-id")
        url = f"{self.host}/chats/{chat_id}/"
        if (message_id := data.get("message-id", None)) is not None:
            url += f"messages/{message_id}/"
        else:
            url += "messages/" if "content" in data.keys() else "presence/"
        return function(self, url, chat_id, user_sessions.sessions[get_jwt_identity()], data)

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

    @parse_chat_data
    def on_open(self, url: str, chat_id: int, session: Session, _):
        session.post(url, json={"online": True})
        join_room(f"chat-{chat_id}")

    @parse_chat_data
    def on_close(self, url: str, chat_id: int, session: Session, _):
        session.post(url, json={"online": False})
        leave_room(f"chat-{chat_id}")

    @parse_chat_data
    def on_send(self, url: str, chat_id: int, session: Session, data: dict):
        session.post(url, json=data)  # add error check
        room_broadcast("send", data, f"chat-{chat_id}")

    @parse_chat_data
    def on_edit(self, url: str, chat_id: int, session: Session, data: dict):
        session.put(url, json=data)  # add error check
        room_broadcast("edit", data, f"chat-{chat_id}")

    @parse_chat_data
    def on_delete(self, url: str, chat_id: int, session: Session, data: dict):
        session.delete(url)  # add error check
        room_broadcast("delete", data, f"chat-{chat_id}")
