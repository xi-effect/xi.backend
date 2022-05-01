from dataclasses import dataclass
from datetime import datetime
from typing import Union

from flask import Flask, send_file
from flask_socketio import disconnect
from pydantic import BaseModel, Field

from __lib__.flask_fullstack import EventGroup as _EventGroup, PydanticModel
from __lib__.flask_siox import Namespace as _Namespace, SocketIO as _SocketIO, ServerEvent, DuplexEvent


@dataclass
class EventException(Exception):
    code: int
    message: str


class EventGroup(_EventGroup):
    from ._core import sessionmaker

    def __init__(self, *args, **kwargs):
        kwargs["sessionmaker"] = kwargs.get("sessionmaker", self.sessionmaker)
        super().__init__(*args, **kwargs)

    def triggers(self, event: ServerEvent, condition: str = None, data: ... = None):
        def triggers_wrapper(function):
            if not hasattr(function, "__sio_doc__"):
                setattr(function, "__sio_doc__", {"x-triggers": []})
            if (x_triggers := function.__sio_doc__.get("x-triggers", None)) is None:
                function.__sio_doc__["x-triggers"] = []
                x_triggers = function.__sio_doc__["x-triggers"]
            x_triggers.append({
                "event": event.name,
                "condition": condition,
                "data": data
            })
            return function

        return triggers_wrapper

    # TODO use .triggers() for bind_pub with use_event (when ffs will support `x-triggers` correctly)

    def doc_abort(self, error_code: Union[int, str], description: str, *, critical: bool = False):
        return self.triggers(error_event, description, {"code": error_code})


class EmptyBody(PydanticModel):
    pass


class Error(BaseModel):
    code: int
    message: str
    event: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow().isoformat())


error_group = EventGroup(use_kebab_case=True)
error_event = error_group.bind_sub(Error, name="error", description="Emitted if something goes wrong")


class Namespace(_Namespace):
    def __init__(self, *args):
        super().__init__(*args)
        self.attach_event_group(error_group)

    def trigger_event(self, event, *args):
        try:
            super().trigger_event(event.replace("-", "_"), *args)
        except EventException as e:
            error_event.emit(code=e.code, message=e.message, event=event)
            disconnect()


class SocketIO(_SocketIO):
    def __init__(self, app: Flask = None, title: str = "SIO", version: str = "1.0.0", **kwargs):
        super().__init__(app, title, version, "/asyncapi.json", **kwargs)  # TODO a file instead

        # @self.on("connect")  # check everytime or save in session?
        # def connect_user():  # https://python-socketio.readthedocs.io/en/latest/server.html#user-sessions
        #     pass             # sio = main.socketio.server

    def init_app(self, app: Flask, **kwargs):
        @app.route("/sio-doc/")
        def get_docs():
            return send_file("../../files/sio-doc/index.html")

        super(SocketIO, self).init_app(app, **kwargs)

    def get_user(self):
        pass


def users_broadcast(_event: Union[ServerEvent, DuplexEvent], _user_ids: list[int], **data):
    for user_id in _user_ids:
        _event.emit(f"user-{user_id}", **data)
