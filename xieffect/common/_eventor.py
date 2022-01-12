from datetime import datetime
from typing import Union

from pydantic import BaseModel, Field

from .flask_siox import Namespace as _Namespace, ServerEvent, DuplexEvent


class Error(BaseModel):
    code: int
    message: str
    event: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow().isoformat())


error_event = ServerEvent(Error, "error")


class Namespace(_Namespace):
    def __init__(self, namespace: str):
        super().__init__(namespace)
        self.attach_event(error_event)

    def trigger_event(self, event, *args):
        super().trigger_event(event.replace("-", "_"), *args)


def users_broadcast(_event: Union[ServerEvent, DuplexEvent], _user_ids: list[int], **data):
    for user_id in _user_ids:
        _event.emit(f"user-{user_id}", **data)
