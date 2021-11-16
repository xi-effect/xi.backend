from dataclasses import dataclass
from typing import Type, Any, Callable

from flask_socketio import emit, Namespace as _Namespace, SocketIO as _SocketIO
from pydantic import BaseModel


def remove_none(data: dict):
    return {key: value for key, value in data.items() if value is not None}


class BaseEvent:  # do not instantiate!
    def __init__(self, name: str = None):
        self.name = None
        if name is not None:
            self.attach_name(name)

    def attach_name(self, name: str):
        raise NotImplementedError

    def create_doc(self, namespace: str):
        raise NotImplementedError


class Event(BaseEvent):  # do not instantiate!
    def __init__(self, model: Type[BaseModel], name: str = None, description: str = None):
        super().__init__(name)
        self.model: Type[BaseModel] = model
        self.description: str = description

    def attach_name(self, name: str):
        self.name = name

    def create_doc(self, namespace: str):
        return remove_none({
            "description": self.description,
            "tags": [{"name": f"namespace-{namespace}"}],
            "message": {"$ref": f"#/components/messages/{self.model.__name__}"}
        })


@dataclass()
class ClientEvent(Event):
    def __init__(self, model: Type[BaseModel], name: str = None, description: str = None, handler: Callable = None):
        super().__init__(model, name, description)
        self.handler: Callable = handler

    def parse(self, data: dict):
        return self.model.parse_obj(data).dict()

    def bind(self, function):
        self.handler = lambda data = None: function(**self.parse(data))

    def create_doc(self, namespace: str):
        return {"publish": super().create_doc(namespace)}


@dataclass()
class ServerEvent(Event):
    def __init__(self, model: Type[BaseModel], name: str = None, description: str = None,
                 include: set[str] = None, exclude: set[str] = None, exclude_none: bool = True):
        super().__init__(model, name, description)
        self._emit_kwargs = {
            "exclude_none": exclude_none,
            "include": include,
            "exclude": exclude,
            "by_alias": True,
        }
        self.model.Config.allow_population_by_field_name = True

    def emit(self, _room: str = None, _data: Any = None, **kwargs):
        if _data is None:
            _data: BaseModel = self.model(**kwargs)
        elif not isinstance(_data, self.model):
            _data: BaseModel = self.model.parse_obj(_data)
        emit(self.name, _data.dict(**self._emit_kwargs), to=_room)

    def create_doc(self, namespace: str):
        return {"subscribe": super().create_doc(namespace)}


@dataclass()
class DuplexEvent(BaseEvent):
    def __init__(self, client_event: ClientEvent = None, server_event: ServerEvent = None,
                 name: str = None, description: str = None):
        super().__init__(name)
        self.client_event: ClientEvent = client_event
        self.server_event: ServerEvent = server_event
        self.description: str = description

    @classmethod
    def similar(cls, model: Type[BaseModel], name: str = None, handler: Callable = None,
                include: set[str] = None, exclude: set[str] = None, exclude_none: bool = True):
        return cls(ClientEvent(model, handler=handler),
                   ServerEvent(model, include=include, exclude=exclude, exclude_none=exclude_none), name)

    def attach_name(self, name: str):
        self.name = name
        self.client_event.name = name
        self.server_event.name = name

    def emit(self, _room: str = None, _data: Any = None, **kwargs):
        return self.server_event.emit(_room, _data, **kwargs)

    def bind(self, function):
        return self.client_event.bind(function)

    def create_doc(self, namespace: str):
        result: dict = self.client_event.create_doc(namespace)
        result.update(self.server_event.create_doc(namespace))
        if self.description is not None:
            result["description"] = self.description
        return result


class EventGroup:
    def __init__(self, **events: [str, BaseEvent]):
        self.events: dict[str, BaseEvent] = events


def kebabify_model(model: Type[BaseModel]):
    for f_name, field in model.__fields__.items():
        field.alias = field.name.replace("_", "-")


class Namespace(_Namespace):
    def __init__(self, namespace=None):
        super().__init__(namespace)
        self.doc_channels = {}
        self.doc_messages = {}

    def attach_event(self, event: BaseEvent, name: str = None, use_kebab_case: bool = False):
        if name is None:
            name = event.name
        self.doc_channels[name.replace("_", "-") if use_kebab_case else name] = event.create_doc(self.namespace)

        if isinstance(event, ClientEvent):
            if event.handler is None:
                pass  # error!
            setattr(self, f"on_{name.replace('-', '_')}", event.handler)

        if isinstance(event, DuplexEvent):
            if event.client_event.handler is None:
                pass  # error!
            setattr(self, f"on_{name.replace('-', '_')}", event.client_event.handler)

            if use_kebab_case:
                kebabify_model(event.client_event.model)
                kebabify_model(event.server_event.model)

            self.doc_messages[event.client_event.model.__name__] = {"payload": event.client_event.model.schema()}
            self.doc_messages[event.server_event.model.__name__] = {"payload": event.server_event.model.schema()}
        else:
            if use_kebab_case:
                kebabify_model(event.model)
            self.doc_messages[event.model.__name__] = {"payload": event.model.schema()}
        # {"name": "", "title": "", "summary": "", "description": ""}

    def attach_event_group(self, event_group: EventGroup, use_kebab_case: bool = False):
        for name, event in event_group.events.items():
            if event.name is None:
                event.attach_name(name.lower().replace("_", "-"))
            self.attach_event(event, use_kebab_case=use_kebab_case)


class SocketIO(_SocketIO):
    def __init__(self, app=None, title: str = "SIO", version: str = "1.0.0", doc_path: str = "/doc/", **kwargs):
        self.async_api = {"asyncapi": "2.2.0", "info": {"title": title, "version": version},
                          "channels": {}, "components": {"messages": {}}}
        self.doc_path = doc_path
        super(SocketIO, self).__init__(app, **kwargs)

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
            self.async_api["components"]["messages"].update(namespace_handler.doc_messages)
        return super(SocketIO, self).on_namespace(namespace_handler)
