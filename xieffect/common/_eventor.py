from datetime import datetime
from typing import Union

from pydantic import BaseModel, Field

from .flask_siox import Namespace as _Namespace, EventGroup, ServerEvent, DuplexEvent


class Error(BaseModel):
    code: int
    message: str
    event: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow().isoformat())


error_group = EventGroup(True)
error_event = error_group.bind_sub("error", "Emitted if something goes wrong", Error)


class Namespace(_Namespace):
    def __init__(self, *args):
        super().__init__(*args)
        self.attach_event_group(error_group)

    def trigger_event(self, event, *args):
        super().trigger_event(event.replace("-", "_"), *args)


def users_broadcast(_event: Union[ServerEvent, DuplexEvent], _user_ids: list[int], **data):
    for user_id in _user_ids:
        _event.emit(f"user-{user_id}", **data)
