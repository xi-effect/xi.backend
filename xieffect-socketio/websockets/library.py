from functools import wraps

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_socketio import Namespace as _Namespace
from requests import Session as _Session, Response

from setup import socketio, user_sessions


def room_broadcast(event: str, data: dict, room: str, namespace: str = "/"):
    socketio.emit(event, data, to=room, namespace=namespace)


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
