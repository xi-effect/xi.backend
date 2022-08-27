from flask import Flask

from __lib__.flask_fullstack import (
    EventController as _EventController,
    PydanticModel,
    SocketIO as _SocketIO,
)


class EventController(_EventController):
    from ._core import sessionmaker  # noqa: WPS436

    def __init__(self, *args, **kwargs):
        kwargs["sessionmaker"] = kwargs.get("sessionmaker", self.sessionmaker)
        kwargs["use_kebab_case"] = kwargs.get("use_kebab_case", True)
        super().__init__(*args, **kwargs)


class EmptyBody(PydanticModel):
    pass


class SocketIO(_SocketIO):
    def __init__(
        self, app: Flask = None, title: str = "SIO", version: str = "1.0.0", **kwargs
    ):
        super().__init__(app, title, version, "/asyncapi.json", **kwargs)

        # check everytime or save in session?
        # https://python-socketio.readthedocs.io/en/latest/server.html#user-sessions
