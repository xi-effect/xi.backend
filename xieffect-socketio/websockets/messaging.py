from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_socketio import join_room, leave_room, rooms
from jwt import decode

from setup import user_sessions, app
from .library import room_broadcast, Namespace, with_request_session, with_arguments, EventArgument as EArg, Session


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
        session = user_sessions.sessions[get_jwt_identity()]
        user_sessions.disconnect(get_jwt_identity())

        chat_ids = [int(chat_id) for room_name in rooms() if (chat_id := room_name.partition("chat-")[2]) != ""]
        session.post(f"{self.host}/chats/close-all/", json={"ids": chat_ids})

    @with_request_session
    @with_arguments(EArg("chat-id"))
    def on_open(self, session: Session, chat_id: int):
        session.post(f"{self.host}/chats/{chat_id}/presence/", json={"online": True})
        join_room(f"chat-{chat_id}")

    @with_request_session
    @with_arguments(EArg("chat-id"))
    def on_close(self, session: Session, chat_id: int):
        session.post(f"{self.host}/chats/{chat_id}/presence/", json={"online": False})
        leave_room(f"chat-{chat_id}")

    @with_request_session
    @with_arguments(EArg("chat-id"), EArg("content", check_only=True), use_original_data=True)
    def on_send(self, session: Session, chat_id: int, data: dict):
        session.post(f"{self.host}/chats/{chat_id}/messages/", json=data)
        room_broadcast("send", data, f"chat-{chat_id}")

    @with_request_session
    @with_arguments(EArg("chat-id"), EArg("message-id"), EArg("content", check_only=True), use_original_data=True)
    def on_edit(self, session: Session, chat_id: int, message_id: int, data: dict):
        session.put(f"{self.host}/chats/{chat_id}/messages/{message_id}/", json=data)
        room_broadcast("edit", data, f"chat-{chat_id}")

    @with_request_session
    @with_arguments(EArg("chat-id"), EArg("message-id"), use_original_data=True)
    def on_delete(self, session: Session, chat_id: int, message_id: int, data: dict):
        session.delete(f"{self.host}/chats/{chat_id}/messages/{message_id}/")
        room_broadcast("delete", data, f"chat-{chat_id}")  # add "message" to data!!!
