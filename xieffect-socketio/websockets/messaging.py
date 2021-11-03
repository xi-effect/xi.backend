from functools import wraps

from requests import Session

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_socketio import join_room, leave_room, Namespace

from setup import storage, app


def with_chat_id(function):
    @jwt_required()
    @wraps(function)
    def with_chat_id_inner(self, data: dict):
        chat_id: int = data.pop("chat-id")
        return function(self, chat_id, data)

    return with_chat_id_inner


class MessagesNamespace(Namespace):
    @jwt_required()  # if not self.authenticate(request.args): raise ConnectionRefusedError("unauthorized!")
    def on_connect(self, _):
        storage[get_jwt_identity()] = request.sid

    @jwt_required()
    def on_disconnect(self):
        storage.pop(get_jwt_identity())

    @with_chat_id
    def on_open(self, chat_id: int, _):
        join_room(f"chat-{chat_id}")

    @with_chat_id
    def on_close(self, chat_id: int, _):
        leave_room(f"chat-{chat_id}")

    def on_send(self, data):
        pass

    def on_edit(self, data):
        pass

    def on_delete(self, data):
        pass
