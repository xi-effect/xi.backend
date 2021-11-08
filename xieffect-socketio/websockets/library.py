from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from json import dumps
from typing import Optional

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_socketio import emit, Namespace as _Namespace
from requests import Session as _Session, Response, post

from setup import socketio, user_sessions, app


def room_broadcast(event: str, data: dict, room: str, namespace: str = "/"):
    socketio.emit(event, data, to=room, namespace=namespace)


def send_discord_message(webhook: str, message: str):
    host = "http://localhost:5000" if app.debug else "https://xieffect.pythonanywhere.com"
    post(f"{host}/webhooks/pass-through/", headers={"Authorization": app.config["API_KEY"]},
         json={"webhook": webhook, "message": message})


def emit_error(message: str, event_name: str, **kwargs):
    kwargs.update({"a": message, "event": event_name, "timestamp": datetime.utcnow().isoformat()})
    emit("error", kwargs)


@dataclass()
class EventArgument:
    name: str
    dest: Optional[str] = None
    desc: Optional[str] = None
    check_only: bool = False

    def __post_init__(self):
        if self.dest is None:
            self.dest = self.name.replace("-", "_")


def with_arguments(*event_args: EventArgument, use_original_data: bool = False):
    def with_arguments_wrapper(function):
        @wraps(function)
        def with_arguments_inner(*args, **kwargs):
            try:
                data: dict = kwargs.get("data") if use_original_data else kwargs.pop("data")
                kwargs.update({arg.dest: data[arg.name] for arg in event_args if not arg.check_only})
                return function(*args, **kwargs)
            except KeyError as e:
                emit_error(f"Argument parsing error, missing '{e}'", function.__name__[3:])

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
            if (a := response.json().get("a", None)) is not None:
                raise RequestException(response.status_code, a)
            else:
                raise RequestException(response.status_code)
        return response


def with_request_session(use_user_id: bool = False, ignore_errors: bool = False):
    def with_request_session_wrapper(function):
        @jwt_required()
        @wraps(function)
        def with_request_session_inner(*args, **kwargs):
            user_id: int = get_jwt_identity()
            kwargs["session"] = user_sessions.sessions[user_id]
            if use_user_id:
                kwargs["user_id"] = user_id
            try:
                return function(*args, **kwargs)
            except RequestException as e:
                if not ignore_errors:
                    e.emit_error_event(function.__name__)

        return with_request_session_inner

    return with_request_session_wrapper


class Namespace(_Namespace):
    def trigger_event(self, event, *args):
        super().trigger_event(event.replace("-", "_"), *args)

    def on_error(self, data):
        send_discord_message("errors", f"Client reported socketio error!\n"
                                       f"```json\n{dumps(data, ensure_ascii=False, indent=2)}\n```")
