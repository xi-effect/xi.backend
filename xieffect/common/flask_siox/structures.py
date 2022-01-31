from collections import OrderedDict
from collections.abc import Callable
from typing import Type

from flask_socketio import Namespace as _Namespace, SocketIO as _SocketIO
from pydantic import BaseModel

from .events import ClientEvent, ServerEvent, DuplexEvent, BaseEvent


def kebabify_model(model: Type[BaseModel]):
    for f_name, field in model.__fields__.items():
        field.alias = field.name.replace("_", "-")


class EventGroup:
    def __init__(self, use_kebab_case: bool = False):
        self.use_kebab_case: bool = use_kebab_case
        self.doc_channels = OrderedDict()
        self.doc_messages = OrderedDict()
        self.handlers = {}

    @staticmethod
    def _kebabify(name: str, model: Type[BaseModel]) -> str:
        kebabify_model(model)
        return name.replace("_", "-")

    def _doc_event(self, event: BaseEvent, model: Type[BaseModel], additional_docs: dict = None):
        self.doc_channels[event.name] = event.create_doc("/", additional_docs)
        self.doc_messages[model.__name__] = {"payload": model.schema()}
        # {"name": "", "title": "", "summary": "", "description": ""}

    def _add_handler(self, name: str, model: Type[BaseModel], function: Callable):
        self.handlers[name] = lambda data=None: function(**model.parse_obj(data).dict())

    def bind_pub(self, name: str, description: str, model: Type[BaseModel]) -> Callable[[Callable], ClientEvent]:
        if self.use_kebab_case:
            name = self._kebabify(name, model)
        event = ClientEvent(model, name, description)

        def bind_pub_wrapper(function) -> ClientEvent:
            self._add_handler(name, model, function)
            self._doc_event(event, model, getattr(function, "__sio_doc__", None))
            return event

        return bind_pub_wrapper

    def bind_sub(self, name: str, description: str, model: Type[BaseModel]) -> ServerEvent:
        if self.use_kebab_case:
            name = self._kebabify(name, model)
        event = ServerEvent(model, name, description)
        self._doc_event(event, model)
        return event

    def bind_dup(self, name: str, description: str, model: Type[BaseModel]) -> Callable[[Callable], DuplexEvent]:
        if self.use_kebab_case:
            name = self._kebabify(name, model)
        event = DuplexEvent.similar(model, name)
        event.description = description

        def bind_dup_wrapper(function) -> DuplexEvent:
            self._add_handler(name, model, function)
            self._doc_event(event, model, getattr(function, "__sio_doc__", None))
            return event

        return bind_dup_wrapper


class Namespace(_Namespace):
    def __init__(self, namespace=None):
        super().__init__(namespace)
        self.doc_channels = OrderedDict()
        self.doc_messages = OrderedDict()

    def attach_event_group(self, event_group: EventGroup):
        self.doc_channels.update(event_group.doc_channels)
        self.doc_messages.update(event_group.doc_messages)
        for name, handler in event_group.handlers.items():
            setattr(self, f"on_{name.replace('-', '_')}", handler)


class SocketIO(_SocketIO):
    def __init__(self, app=None, title: str = "SIO", version: str = "1.0.0", doc_path: str = "/doc/", **kwargs):
        self.async_api = {"asyncapi": "2.2.0", "info": {"title": title, "version": version},
                          "channels": OrderedDict(), "components": {"messages": OrderedDict()}}
        self.doc_path = doc_path
        super(SocketIO, self).__init__(app, **kwargs)

    def docs(self):
        return self.async_api

    def init_app(self, app, **kwargs):
        app.config["JSON_SORT_KEYS"] = False  # TODO kinda bad for a library

        @app.route(self.doc_path)
        def documentation():
            return self.docs()

        return super(SocketIO, self).init_app(app, **kwargs)

    def on_namespace(self, namespace_handler):
        if isinstance(namespace_handler, Namespace):
            self.async_api["channels"].update(namespace_handler.doc_channels)
            self.async_api["components"]["messages"].update(namespace_handler.doc_messages)
        return super(SocketIO, self).on_namespace(namespace_handler)
