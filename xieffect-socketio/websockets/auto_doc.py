from dataclasses import dataclass
from enum import Enum
from typing import Type, Any

from flask_socketio import emit

from .library import EventArgument as EArg, Namespace as _Namespace


@dataclass()
class Event:
    name: str
    arguments: list[EArg] = None

    def __post_init__(self):
        if self.arguments is None:
            self.arguments = []


class ClientEvent(Event):
    def parse_incoming(self, data: dict):
        return {arg.dest: data[arg.name] if arg.required is None else data.get(arg.name, arg.default)
                for arg in self.arguments if not arg.check_only}


class ServerEvent(Event):
    def collect_outgoing(self, data: dict):
        return {arg.name: data[arg.dest] if arg.required is None else data.get(arg.dest, arg.default)
                for arg in self.arguments}

    def emit(self, data: Any, room: str = None):
        emit(self.name, self.collect_outgoing(data), to=room)


@dataclass()
class DuplexEvent(ClientEvent, ServerEvent):
    client_arguments: list[EArg] = None
    server_arguments: list[EArg] = None

    def __post_init__(self):
        super(DuplexEvent, self).__post_init__()
        if self.client_arguments is None:
            self.client_arguments = []
        if self.server_arguments is None:
            self.server_arguments = []
        self.client_arguments.extend(self.arguments)
        self.server_arguments.extend(self.arguments)

    def parse_incoming(self, data: dict):
        return {arg.dest: data[arg.name] if arg.required is None else data.get(arg.name, arg.default)
                for arg in self.client_arguments if not arg.check_only}

    def collect_outgoing(self, data: dict):
        return {arg.name: data[arg.dest] if arg.required is None else data.get(arg.dest, arg.default)
                for arg in self.server_arguments}


class EventGroup(Enum):
    @classmethod
    def extract(cls):
        # cls.__members__.values()
        pass


class Namespace(_Namespace):
    def attach_event_group(self, cls: Type[EventGroup]):
        for name, member in cls.__members__.items():
            if isinstance(member, ClientEvent):
                if (method := getattr(cls, f"on_{name.lower()}", None)) is not None:
                    setattr(self, f"on_{name.lower()}", lambda data: method(**member.parse_incoming(data)))
                else:
                    pass  # some sort of warning

                pass  # documenting

            if isinstance(member, ServerEvent):
                pass  # documenting

    # def __init__(self, socketio):
    #     self.socketio = socketio
    #
    # def _bind_event(self, event: Event):
    #     event.socketio = self.socketio
    #
    # def bind_client_event(self, event: ClientEvent, handler: Callable):
    #     def handler_after(data):
    #         return handler(**event.parse_incoming(data))
    #
    #     self._bind_event(event)
    #     setattr(self, f"on_{event.name}", handler_after)
    #
    # def bind_server_event(self, event: ServerEvent):
    #     self._bind_event(event)
    #     setattr(self, f"emit_{event.name}", event.emit)
    #
    # def client_event(self, event: ClientEvent):
    #     def client_event_wrapper(function):
    #         self.bind_client_event(event, function)
    #
    #     return client_event_wrapper
    #
    # def duplex_event(self, event: DuplexEvent):
    #     def duplex_event_wrapper(function):
    #         self.bind_client_event(event, function)
    #         self.bind_server_event(event)
    #
    #     return duplex_event_wrapper
    #
    # def bind_client_event2(self, event: ClientEvent, handler: Callable):
    #     self.bind_client_event(event, with_request_session()(handler))
