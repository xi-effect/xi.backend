from flask import Flask
from flask_fullstack import SocketIOTestClient

from common import SocketIO
from test.conftest import FlaskTestClient


class DoubleClient:
    def __init__(self, rst_client: FlaskTestClient, sio_client: SocketIOTestClient):
        self.rst: FlaskTestClient = rst_client
        self.sio: SocketIOTestClient = sio_client

    @classmethod
    def from_app(cls, app: Flask):
        rst_client = app.test_client()
        sio_client = SocketIOTestClient(rst_client)
        return cls(rst_client, sio_client)

    @classmethod
    def from_flask(cls, flask_client: FlaskTestClient):
        return cls(flask_client, SocketIOTestClient(flask_client))

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

    def connect_user(self, flask_client: FlaskTestClient = None) -> DoubleClient:
        if flask_client is None:
            return DoubleClient.from_app(self.app)
        return DoubleClient.from_flask(flask_client)

    def attach_user(self, username: str) -> None:
        self.users[username] = self.connect_user()

    def disconnect_user(self, username: str) -> None:
        self.users.pop(username).__exit__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        for user in self.users.values():
            user.__exit__()
        self.users.clear()
