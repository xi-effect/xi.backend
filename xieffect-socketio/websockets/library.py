from dataclasses import dataclass
from functools import wraps
from json import dumps
from typing import Optional, Any

from flask_socketio import Namespace as _Namespace
from requests import post

from library import RequestException as _RequestException, emit_error
from library0 import ServerEvent
from setup import app


def send_discord_message(webhook: str, message: str):
    if not app.debug:
        host = "https://xieffect.pythonanywhere.com"
        post(f"{host}/webhooks/pass-through/", headers={"Authorization": app.config["API_KEY"]},
             json={"webhook": webhook, "message": message})


class RequestException(_RequestException):
    def send_discord_message(self, webhook: str, message: str):
        send_discord_message(webhook, message)


def users_broadcast(event: ServerEvent, data: dict, user_ids: list[int]):
    for user_id in user_ids:
        event.emit(f"user-{user_id}", data)


@dataclass()
class EventArgument:
    name: str
    default: Optional[Any] = None
    dest: Optional[str] = None
    desc: Optional[str] = None
    check_only: bool = False
    required: bool = True

    def __post_init__(self):
        if self.dest is None:
            self.dest = self.name.replace("-", "_")
        if self.default is not None:
            self.required = False


def with_arguments(*event_args: EventArgument, use_original_data: bool = True):
    def with_arguments_wrapper(function):
        @wraps(function)
        def with_arguments_inner(*args, **kwargs):
            try:
                data: dict = kwargs.get("data") if use_original_data else kwargs.pop("data")
                kwargs.update({arg.dest: data[arg.name] if arg.required is None else data.get(arg.name, arg.default)
                               for arg in event_args if not arg.check_only})
                return function(*args, **kwargs)
            except KeyError as e:
                emit_error(f"Argument parsing error, missing '{e}'", function.__name__[3:])

        return with_arguments_inner

    return with_arguments_wrapper


class Namespace(_Namespace):
    def trigger_event(self, event, *args):
        super().trigger_event(event.replace("-", "_"), *args)

    def on_error(self, data):
        send_discord_message("errors", f"Client reported socketio error!\n"
                                       f"```json\n{dumps(data, ensure_ascii=False, indent=2)}\n```")
