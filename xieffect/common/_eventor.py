from __future__ import annotations

from flask import Flask

from __lib__.flask_fullstack import (
    EventController as _EventController,
    PydanticModel,
    SocketIO as _SocketIO,
)
from ._core import sessionmaker  # noqa: WPS436


class EventController(_EventController):
    def __init__(self, *args, **kwargs):
        kwargs["sessionmaker"] = kwargs.get("sessionmaker", sessionmaker)
        kwargs["use_kebab_case"] = kwargs.get("use_kebab_case", True)
        super().__init__(*args, **kwargs)


class EmptyBody(PydanticModel):
    pass


class SocketIO(_SocketIO):
    def __init__(
        self,
        app: Flask = None,
        title: str = "SIO",
        version: str = "1.0.0",
        **kwargs,
    ):
        super().__init__(
            app,
            title,
            version,
            doc_path="/asyncapi.json",
            remove_ping_pong_logs=True,
            **kwargs,
        )

        # check everytime or save in session?
        # https://python-socketio.readthedocs.io/en/latest/server.html#user-sessions
