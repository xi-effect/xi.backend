from dataclasses import dataclass
from functools import wraps
from typing import Optional

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_socketio import Namespace as _Namespace
from requests import Session as _Session, Response

from setup import socketio, user_sessions


def room_broadcast(event: str, data: dict, room: str, namespace: str = "/"):
    socketio.emit(event, data, to=room, namespace=namespace)


@dataclass()
class EventArgument:
    name: str
    dest: Optional[str] = None
    desc: Optional[str] = None

    def __post_init__(self):
        if self.dest is None:
            self.dest = self.name.replace("-", "_")


def with_arguments(*event_args: EventArgument):
    def with_arguments_wrapper(function):
        @wraps(function)
        def with_arguments_inner(*args, **kwargs):
            try:
                data: dict = kwargs.pop("data")
                kwargs.update({arg.dest: data[arg.name] for arg in event_args})
                return function(*args, **kwargs)
            except KeyError as e:
                pass  # error check

        return with_arguments_inner

    return with_arguments_wrapper


@dataclass()
class RequestException(Exception):
    code: int
    message: str = None
    client_fault: bool = None
    server_fault: bool = None

    def __post_init__(self):
        self.client_fault = self.code in (401, 403, 404, 422)
        self.server_fault = self.code in (400, 401, 422)

    def emit_error_event(self, event_name: str):
        if self.server_fault:
            send_discord_message("errors", f"Socket-IO server {self.code}-error appeared!\n`{self.message}`")
        if self.client_fault:
            emit_error(self.message, event_name, code=self.code)
        else:
            emit_error("Server error appeared. It was reported to discord", event_name, code=500)


class Session(_Session):
    def request(self, *args, **kwargs):
        response: Response = super(Session, self).request(*args, **kwargs)
        if 400 <= response.status_code < 500:
            pass  # error check
        return response


def with_request_session(function):
    @jwt_required()
    @wraps(function)
    def with_request_session_inner(*args, **kwargs):
        kwargs["session"] = user_sessions.sessions[get_jwt_identity()]
        return function(*args, **kwargs)

    return with_request_session_inner


class Namespace(_Namespace):
    def trigger_event(self, event, *args):
        super().trigger_event(event.replace("-", "_"), *args)
