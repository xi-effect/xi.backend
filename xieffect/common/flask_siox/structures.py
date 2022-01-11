from collections import OrderedDict
from typing import Type

from flask_socketio import Namespace as _Namespace, SocketIO as _SocketIO
from pydantic import BaseModel

from .events import BaseEvent, ClientEvent, DuplexEvent


class EventGroup:
    def __init__(self, **events: [str, BaseEvent]):
        self.events: dict[str, BaseEvent] = events


def kebabify_model(model: Type[BaseModel]):
    for f_name, field in model.__fields__.items():
        field.alias = field.name.replace("_", "-")


class Namespace(_Namespace):
    def __init__(self, namespace=None):
        super().__init__(namespace)
        self.doc_channels = OrderedDict()
        self.doc_messages = OrderedDict()

    def attach_event(self, event: BaseEvent, name: str = None, use_kebab_case: bool = False):
        if name is None:
            name = event.name
        self.doc_channels[name.replace("_", "-") if use_kebab_case else name] = event.create_doc(self.namespace)

        if isinstance(event, ClientEvent):
            if event.handler is None:
                pass  # TODO error / warning
            setattr(self, f"on_{name.replace('-', '_')}", event.handler)

        if isinstance(event, DuplexEvent):
            if event.client_event.handler is None:
                pass  # TODO error / warning
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
