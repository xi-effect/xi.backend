from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restx import Api
from flask_socketio import rooms

from library import Session
from setup import socketio, app, user_sessions
from websockets import TestNamespace, Namespace, messaging_events, chat_management_events, user_management_events
from temp_api import reglog_namespace, static_namespace

api = Api(app, doc="/doc/")
api.add_namespace(static_namespace)
api.add_namespace(reglog_namespace)


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
messages_namespace.attach_event_group(messaging_events)
messages_namespace.attach_event_group(chat_management_events)
messages_namespace.attach_event_group(user_management_events)

socketio.on_namespace(TestNamespace("/test"))
socketio.on_namespace(messages_namespace)

if __name__ == "__main__":
    socketio.run(app, port=5050, debug=True)
