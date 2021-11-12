from dataclasses import dataclass
from enum import Enum
from typing import Type, Any, Callable

from flask_socketio import emit, Namespace as _Namespace
from pydantic import BaseModel


@dataclass()
class Event:
    model: Type[BaseModel]
    name: str = None


@dataclass()
class ClientEvent(Event):
    handler: Callable = None

    def parse(self, data: dict):
        return self.model.parse_obj(data).dict()

    def bind(self, function):
        self.handler = lambda data: function(**self.parse(data))


@dataclass()
class ServerEvent(Event):
    include: set[str] = None
    exclude: set[str] = None
    exclude_none: bool = True

    def __post_init__(self):
        if self.include is None:
            self.include = set()
        if self.exclude is None:
            self.exclude = set()

        self._emit_kwargs = {
            "exclude_none": self.exclude_none,
            "include": self.include,
            "exclude": self.exclude,
            "by_alias": True,
        }

    def emit(self, _room: str = None, _data: Any = None, **kwargs):
        if _data is None:
            _data: BaseModel = self.model(**kwargs)
        elif not isinstance(_data, self.model):
            _data: BaseModel = self.model.parse_obj(_data)
        emit(self.name, _data.dict(**self._emit_kwargs), to=_room)


class DuplexEvent(ServerEvent, ClientEvent):
    pass


class EventGroup(Enum):
    pass


class Namespace(_Namespace):
    def attach_event_group(self, cls: Type[EventGroup]):
        for name, member in cls.__members__.items():
            if isinstance(member, Event):
                member.name = name.lower()

            if isinstance(member, ClientEvent):
                if member.handler is None:
                    pass  # error!
                setattr(self, f"on_{member.name}", member.handler)

                pass  # documenting

            if isinstance(member, ServerEvent):
                pass  # documenting
