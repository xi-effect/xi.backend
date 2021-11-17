from dataclasses import dataclass

from flask import Flask
from flask.testing import FlaskClient
from flask_socketio.test_client import SocketIOTestClient

from library0 import SocketIO


@dataclass
class Event:
    name: str
    data: dict
    namespace: str = "/"

    @classmethod
    def from_sio(cls, event: dict):
        return cls(event["name"], event["args"][0], event.get("namespace", "/"))


class DoubleClient:
    def __init__(self, app: Flask, socketio: SocketIO, flask_client: FlaskClient = None):
        if flask_client is None:
            flask_client = app.test_client()
        self.rst: FlaskClient = flask_client
        self.sio: SocketIOTestClient = socketio.test_client(app, flask_test_client=self.rst)

    def __enter__(self):
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self.rst.__exit__(exc_type, exc_val, exc_tb)
        self.sio.disconnect()


class MultiClient:
    def __init__(self, app: Flask, socketio: SocketIO):
        self.app: Flask = app
        self.socketio: SocketIO = socketio
        self.users: dict[str, DoubleClient] = {}

    def __enter__(self):
        return self

    def connect_user(self, flask_client: FlaskClient = None) -> DoubleClient:
        return DoubleClient(self.app, self.socketio, flask_client)

    def attach_user(self, username: str) -> None:
        self.users[username] = self.connect_user()

    def disconnect_user(self, username: str) -> None:
        self.users.pop(username).__exit__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        for user in self.users.values():
            user.__exit__()
        self.users.clear()
