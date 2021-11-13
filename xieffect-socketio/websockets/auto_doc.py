from dataclasses import dataclass
from enum import Enum
from typing import Type, Any, Callable

from flask_socketio import emit, Namespace as _Namespace, SocketIO as _SocketIO
from pydantic import BaseModel


def remove_none(data: dict):
    return {key: value for key, value in data.items() if value is not None}


@dataclass()
class Event:
    model: Type[BaseModel]
    name: str = None
    summary: str = None
    description: str = None

    def create_doc(self, namespace: str):
        return remove_none({
            "summary": self.summary, "description": self.description,
            "tags": [{"name": f"namespace-{namespace}"}],
            "message": {"$ref": f"#/components/messages/{self.model.__name__}"}
        })


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
    def __init__(self, namespace=None):
        super().__init__(namespace)
        self.doc_channels = {}
        self.doc_messages = {}

    def attach_event_group(self, cls: Type[EventGroup]):
        for name, member in cls.__members__.items():
            if not isinstance(member, Event):
                continue

            member.name = name.lower()
            doc_data = {"description": ""}
            event_doc = member.create_doc(self.namespace)

            if isinstance(member, ClientEvent):
                if member.handler is None:
                    pass  # error!
                setattr(self, f"on_{member.name}", member.handler)
                doc_data["publish"] = event_doc

            if isinstance(member, ServerEvent):
                doc_data["subscribe"] = event_doc

            self.doc_channels[member.name] = doc_data
            self.doc_messages[member.model.__name__] = {"payload": member.model.schema()}
            # {"name": "", "title": "", "summary": "", "description": ""}


class SocketIO(_SocketIO):
    def __init__(self, title: str = "SIO", version: str = "1.0.0", doc_path: str = "/"):
        self.async_api = {"asyncapi": "2.2.0", "info": {"title": title, "version": version},
                          "channels": {}, "components": {"schemas": {}}}
        self.doc_path = doc_path

    def docs(self):
        return self.async_api

    def init_app(self, app, **kwargs):
        @app.route(self.doc_path)
        def documentation():
            return self.docs()

        return super(SocketIO, self).init_app(app, **kwargs)

    def on_namespace(self, namespace_handler):
        if isinstance(namespace_handler, Namespace):
            self.async_api["channels"].update(namespace_handler.doc_channels)
            self.async_api["components"]["schemas"].update(namespace_handler.doc_messages)
        return super(SocketIO, self).on_namespace(namespace_handler)
