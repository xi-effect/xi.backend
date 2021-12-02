from dataclasses import dataclass
from typing import Callable

from flask import Flask
from flask.testing import FlaskClient
from flask_socketio.test_client import SocketIOTestClient as _SocketIOTestClient

from library0 import SocketIO


@dataclass
class Event:
    name: str
    data: dict
    namespace: str = "/"

    @classmethod
    def from_sio(cls, event: dict):
        return cls(event["name"], event["args"][0], event.get("namespace", "/"))

    def __eq__(self, other):
        return isinstance(other, Event) and self.name == other.name \
               and self.data == other.data and self.name == other.namespace


class SocketIOTestClient(_SocketIOTestClient):
    def _get_received(self, condition: Callable[[dict], bool] = lambda pkt: True, namespace: str = "/",
                      keep_history: bool = False) -> list[Event]:
        if not self.is_connected(namespace):
            raise RuntimeError("not connected")
        result = [pkt for pkt in self.queue[self.eio_sid] if condition(pkt)]
        if not keep_history:
            self.queue[self.eio_sid] = [pkt for pkt in self.queue[self.eio_sid] if pkt not in result]
        return [Event.from_sio(pkt) for pkt in result]

    def get_received(self, namespace: str = "/", keep_history: bool = False) -> list[Event]:
        return self._get_received(lambda pkt: pkt["namespace"] == namespace, namespace, keep_history)

    def filter_received(self, event_name: str, namespace: str = "/", keep_history: bool = False) -> list[Event]:
        return self._get_received(lambda pkt: pkt["namespace"] == namespace and pkt["name"] == event_name,
                                  namespace, keep_history)

    def sort_received(self, event_names: list[str], namespace: str = "/", collect_rest: bool = True,
                      keep_history: bool = False) -> dict[str, list[Event]]:
        if collect_rest:
            event_names.append("*")
        return {name: [event for event in self.get_received(namespace, keep_history)
                       if event.namespace == namespace and (name == "*" or event.name == name)]
                for name in event_names}

    def received_count(self, namespace: str = "/"):
        return len(self.get_received(namespace, keep_history=True))


class DoubleClient:
    def __init__(self, app: Flask, socketio: SocketIO, flask_client: FlaskClient = None):
        if flask_client is None:
            flask_client = app.test_client()
        self.rst: FlaskClient = flask_client
        self.sio: SocketIOTestClient = SocketIOTestClient(app, socketio, flask_test_client=self.rst)

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
