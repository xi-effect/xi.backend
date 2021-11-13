from json import dumps
from typing import Union

from requests import post

from library import RequestException as _RequestException, error_event
from library0 import ServerEvent, Namespace as _Namespace, DuplexEvent
from setup import app  # temp


def send_discord_message(webhook: str, message: str):
    if not app.debug:
        host = "https://xieffect.pythonanywhere.com"
        post(f"{host}/webhooks/pass-through/", headers={"Authorization": app.config["API_KEY"]},
             json={"webhook": webhook, "message": message})


class RequestException(_RequestException):
    def send_discord_message(self, webhook: str, message: str):
        send_discord_message(webhook, message)


def users_broadcast(_event: Union[ServerEvent, DuplexEvent], _user_ids: list[int], **data):
    for user_id in _user_ids:
        _event.emit(f"user-{user_id}", **data)


# error_event.emit(message=f"Argument parsing error, missing '{e}'", event=function.__name__, code=400)


class Namespace(_Namespace):
    def __init__(self, namespace: str):
        super().__init__(namespace)
        self.attach_event(error_event)

    def trigger_event(self, event, *args):
        super().trigger_event(event.replace("-", "_"), *args)

    def on_error(self, data):
        send_discord_message("errors", f"Client reported socketio error!\n"
                                       f"```json\n{dumps(data, ensure_ascii=False, indent=2)}\n```")
