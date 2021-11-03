from requests import post, put, delete

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_socketio import join_room, leave_room, Namespace

from setup import socketio, storage, app


class MessagesNamespace(Namespace):
    @jwt_required()  # if not self.authenticate(request.args): raise ConnectionRefusedError("unauthorized!")
    def on_connect(self, _):
        storage[get_jwt_identity()] = request.sid

    @jwt_required()
    def on_disconnect(self):
        storage.pop(get_jwt_identity())

    @jwt_required()
    def on_open(self, data):
        chat_id: int = data["chat-id"]
        join_room(f"chat-{chat_id}")

    @jwt_required()
    def on_close(self, data):
        chat_id: int = data["chat-id"]
        leave_room(f"chat-{chat_id}")

    def on_send(self, data):
        pass

    def on_edit(self, data):
        pass

    def on_delete(self, data):
        pass
