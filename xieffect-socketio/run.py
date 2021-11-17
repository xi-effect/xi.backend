from urllib.parse import urlparse, urljoin

from flask import redirect, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import rooms

from library import Session
from setup import socketio, app, user_sessions
from websockets import Namespace, messaging_events, chat_management_events, user_management_events


class MessagesNamespace(Namespace):
    def __init__(self, namespace=None):
        super().__init__(namespace)

    @jwt_required()  # if not self.authenticate(request.args): raise ConnectionRefusedError("unauthorized!")
    def on_connect(self, _):
        user_sessions.connect(get_jwt_identity())

    @user_sessions.with_request_session(use_user_id=True, ignore_errors=True)
    def on_disconnect(self, session: Session, user_id: int):
        user_sessions.disconnect(user_id)
        chat_ids = [int(chat_id) for room_name in rooms() if (chat_id := room_name.partition("chat-")[2]) != ""]
        session.post(f"{app.config['host']}/chat-temp/close-all/", json={"ids": chat_ids})


messages_namespace = MessagesNamespace("/")
messages_namespace.attach_event_group(messaging_events, use_kebab_case=True)
messages_namespace.attach_event_group(chat_management_events, use_kebab_case=True)
messages_namespace.attach_event_group(user_management_events, use_kebab_case=True)

socketio.on_namespace(messages_namespace)


@app.before_request
def main_server():
    path = urlparse(request.url).path
    if path != "/socket.io/":
        return redirect(urljoin(app.config["host"], path))


if __name__ == "__main__":
    socketio.run(app, port=5050, debug=True)
