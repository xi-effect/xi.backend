from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Union

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_socketio import join_room, close_room
from pydantic import BaseModel, Field
from requests import Session as _Session, Response

from library0 import ServerEvent, DuplexEvent


class Error(BaseModel):
    code: int
    message: str
    event: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow().isoformat())


error_event = ServerEvent(Error, "error")


@dataclass()
class RequestException(Exception):
    code: int
    message: str = None
    client_fault: bool = None
    server_fault: bool = None

    def __post_init__(self):
        self.client_fault = self.code in (401, 403, 404, 422)
        self.server_fault = self.code in (400, 401, 422)

    @staticmethod
    def send_discord_message(webhook: str, message: str):
        raise NotImplementedError  # temp

    def emit_error_event(self, event_name: str):
        if self.server_fault:
            self.send_discord_message("errors", f"Socket-IO server {self.code}-error appeared!\n`{self.message}`")
        if self.client_fault:
            error_event.emit(message=self.message, event=event_name, code=self.code)
        else:
            error_event.emit(message="Server error was reported to discord", event=event_name, code=500)


def users_broadcast(_event: Union[ServerEvent, DuplexEvent], _user_ids: list[int], **data):
    for user_id in _user_ids:
        _event.emit(f"user-{user_id}", **data)


class Session(_Session):
    def request(self, *args, **kwargs):
        response: Response = super(Session, self).request(*args, **kwargs)
        if 400 <= response.status_code < 500:
            if (a := response.json().get("a", None)) is not None:
                raise RequestException(response.status_code, a)
            else:
                raise RequestException(response.status_code)
        return response


class UserSession:
    def __init__(self):
        self.sessions: dict[int, Session] = dict()
        self.counters: dict[int, int] = dict()

    def connect(self, user_id: int):
        if user_id in self.sessions.keys():
            self.sessions[user_id] = Session()
            self.sessions[user_id].cookies.set("access_token_cookie", request.cookies["access_token_cookie"])
            self.counters[user_id] = 1
        else:
            self.counters[user_id] += 1
        join_room(f"user-{user_id}")

    def disconnect(self, user_id: int):
        self.counters[user_id] -= 1
        if self.counters[user_id] == 0:
            self.sessions.pop(user_id)
            self.counters.pop(user_id)
            close_room(f"user-{user_id}")

    def with_request_session(self, use_user_id: bool = False, ignore_errors: bool = False):
        def with_request_session_wrapper(function):
            @jwt_required()
            @wraps(function)
            def with_request_session_inner(*args, **kwargs):
                user_id: int = get_jwt_identity()
                kwargs["session"] = self.sessions[user_id]
                if use_user_id:
                    kwargs["user_id"] = user_id
                try:
                    return function(*args, **kwargs)
                except RequestException as e:
                    if not ignore_errors:
                        e.emit_error_event(function.__name__)

            return with_request_session_inner

        return with_request_session_wrapper
