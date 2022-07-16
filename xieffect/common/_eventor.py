from flask import Flask

from __lib__.flask_fullstack import EventController as _EventController, PydanticModel, SocketIO as _SocketIO


# DEPRECATED due to support for acknowledgements
# @dataclass
# class EventException(Exception):
#     code: int
#     message: str


class EventController(_EventController):
    from ._core import sessionmaker

    def __init__(self, *args, **kwargs):
        kwargs["sessionmaker"] = kwargs.get("sessionmaker", self.sessionmaker)
        kwargs["use_kebab_case"] = kwargs.get("use_kebab_case", True)
        super().__init__(*args, **kwargs)

    # DEPRECATED due to support for acknowledgements
    # def triggers(self, event: ServerEvent, condition: str = None, data: ... = None):
    #     def triggers_wrapper(function):
    #         if not hasattr(function, "__sio_doc__"):
    #             setattr(function, "__sio_doc__", {"x-triggers": []})
    #         if (x_triggers := function.__sio_doc__.get("x-triggers", None)) is None:
    #             function.__sio_doc__["x-triggers"] = []
    #             x_triggers = function.__sio_doc__["x-triggers"]
    #         x_triggers.append({
    #             "event": event.name,
    #             "condition": condition,
    #             "data": data
    #         })
    #         return function

    #    return triggers_wrapper

    # T/O/D/O use .triggers() for bind_pub with use_event (when ffs will support `x-triggers` correctly)

    # def doc_abort(self, error_code: Union[int, str], description: str, *, critical: bool = False):
    #    return self.triggers(error_event, description, {"code": error_code})


class EmptyBody(PydanticModel):
    pass


class SocketIO(_SocketIO):
    def __init__(self, app: Flask = None, title: str = "SIO", version: str = "1.0.0", **kwargs):
        super().__init__(app, title, version, "/asyncapi.json", **kwargs)

        # @self.on("connect")  # check everytime or save in session?
        # def connect_user():  # https://python-socketio.readthedocs.io/en/latest/server.html#user-sessions
        #     pass             # sio = main.socketio.server
