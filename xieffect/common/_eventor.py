from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Union, Type

from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import disconnect
from pydantic import BaseModel, Field

from ._interfaces import Identifiable, UserRole
from ._sqlalchemy import Sessionmaker
from ._utils import get_or_pop
from .flask_siox import Namespace as _Namespace, EventGroup as _EventGroup, SocketIO as _SocketIO
from .flask_siox import ServerEvent, DuplexEvent


# TODO `from .main import sessionmaker` for xieffect-specific


@dataclass
class EventException(Exception):
    code: int
    message: str


class EventGroup(_EventGroup):
    def __init__(self, sessionmaker: Sessionmaker, use_kebab_case: bool = False):
        super().__init__(use_kebab_case)
        self.with_begin = sessionmaker.with_begin

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

        return triggers_wrapper

    def abort(self, error_code: Union[int, str], description: str):
        raise EventException(error_code, description)

    def _database_searcher(self, identifiable: Type[Identifiable], check_only: bool, no_id: bool,
                           use_session: bool, error_code: int, callback, args, kwargs, *,
                           input_field_name: Union[str, None] = None, result_field_name: Union[str, None] = None):
        if input_field_name is None:
            input_field_name = identifiable.__name__.lower() + "_id"
        if result_field_name is None:
            result_field_name = identifiable.__name__.lower()
        session = get_or_pop(kwargs, "session", use_session)
        target_id: int = get_or_pop(kwargs, input_field_name, check_only and not no_id)
        if (result := identifiable.find_by_id(session, target_id)) is None:
            self.abort(error_code, identifiable.not_found_text)
        else:
            if not check_only:
                kwargs[result_field_name] = result
            return callback(*args, **kwargs)

    def database_searcher(self, identifiable: Type[Identifiable], *, result_field_name: Union[str, None] = None,
                          check_only: bool = False, use_session: bool = False):
        """
        - Uses incoming id argument to find something :class:`Identifiable` in the database.
        - If the entity wasn't found, will return a 404 response, which is documented automatically.
        - Can pass (entity's id or entity) and session objects to the decorated function.

        :param identifiable: identifiable to search for
        :param result_field_name: overrides default name of found object [default is identifiable.__name__.lower()]
        :param check_only: (default: False) if True, checks if entity exists and passes id to the decorated function
        :param use_session: (default: False) whether to pass the session to the decorated function
        """

        def searcher_wrapper(function):
            @wraps(function)
            @self.triggers(error_event, identifiable.not_found_text, {"code": 404})
            @self.with_begin
            def searcher_inner(*args, **kwargs):
                return self._database_searcher(identifiable, check_only, False, use_session, 404,
                                               function, args, kwargs, result_field_name=result_field_name)

            return searcher_inner

        return searcher_wrapper

    def jwt_authorizer(self, role: Type[UserRole], optional: bool = False,
                       check_only: bool = False, use_session: bool = True):
        """
        - Authorizes user by JWT-token.
        - If token is missing or is not processable, falls back on flask-jwt-extended error handlers.
        - If user doesn't exist or doesn't have the role required, sends the corresponding response.
        - All error responses are added to the documentation automatically.
        - Can pass user and session objects to the decorated function.

        :param role: role to expect
        :param optional: (default: False)
        :param check_only: (default: False) if True, user object won't be passed to the decorated function
        :param use_session: (default: True) whether to pass the session to the decorated function
        """

        def authorizer_wrapper(function):  # TODO see notes in SocketIO.__init__ below!
            error_code: int = 401 if role is UserRole.default_role else 403

            @wraps(function)
            @self.triggers(error_event, role.not_found_text, {"code": error_code})
            @jwt_required(optional=optional)
            @self.with_begin
            def authorizer_inner(*args, **kwargs):
                if (jwt := get_jwt_identity()) is None and optional:
                    kwargs[role.__name__.lower()] = None
                    return function(*args, **kwargs)
                kwargs["_jwt"] = jwt
                return self._database_searcher(role, check_only, True, use_session, error_code,
                                               function, args, kwargs, input_field_name="_jwt")

            return authorizer_inner

        return authorizer_wrapper


class Error(BaseModel):
    code: int
    message: str
    event: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow().isoformat())


error_group = EventGroup(None, True)  # TODO fix
error_event = error_group.bind_sub("error", "Emitted if something goes wrong", Error)


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
    def __init__(self, app=None, title: str = "SIO", version: str = "1.0.0", doc_path: str = "/doc/", **kwargs):
        super().__init__(app, title, version, doc_path, **kwargs)

        # @self.on("connect")  # check everytime or save in session?
        # def connect_user():  # https://python-socketio.readthedocs.io/en/latest/server.html#user-sessions
        #     pass             # sio = main.socketio.server

    def get_user(self):
        pass


def users_broadcast(_event: Union[ServerEvent, DuplexEvent], _user_ids: list[int], **data):
    for user_id in _user_ids:
        _event.emit(f"user-{user_id}", **data)
