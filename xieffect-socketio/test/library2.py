from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Iterator
from urllib.parse import urljoin

from requests import Session as _Session
from socketio.client import Client as _Client


@dataclass()
class Event:
    name: str
    data: Any


class AnyClient:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.exit()

    def exit(self):
        raise NotImplementedError


class Session(_Session, AnyClient):
    def __init__(self, prefix_url: str = None):
        super(Session, self).__init__()
        self.prefix_url = prefix_url

    def request(self, method: str, url: str, *args, **kwargs):
        return super().request(method, urljoin(self.prefix_url, url), *args, **kwargs)

    def exit(self):
        self.close()


class Client(_Client, AnyClient):
    def __init__(self, url: str, connection_kwargs, default_kwargs):
        super(Client, self).__init__()

        kwargs = default_kwargs.copy()
        kwargs.update(connection_kwargs)
        self.connect(url, **kwargs)
        self.on("*", self.handler)

        self.events: list[Event] = []
        self.stop: bool = False

    def exit(self):
        self.disconnect()

    def emit(self, event, data=None, namespace=None, callback=None, wait_stop: bool = False):
        super(Client, self).emit(event, data, namespace, callback)
        if wait_stop:
            self.wait_stop()

    def handler(self, event: str, data: Any = None):
        if event == "stop":
            self.stop = True
        else:
            self.events.append(Event(event, data))

    def next_new_event(self) -> Optional[Event]:
        if len(self.events) == 0:
            return None
        return self.events.pop(0)

    def new_events(self) -> Iterator[Event]:
        while (new_event := self.next_new_event()) is not None:
            yield new_event

    def new_event_count(self) -> int:
        return len(self.events)

    def wait_stop(self):
        self.emit("stop")
        while not self.stop:
            self.sleep(1)


class HClient(Client):
    def __init__(self, url: str, connection_kwargs, default_kwargs):
        super().__init__(url, connection_kwargs, default_kwargs)
        self.new_events_position: int = 0

    def next_new_event(self) -> Optional[Event]:
        if self.new_events_position == len(self.events):
            return None
        self.new_events_position += 1
        return self.events[self.new_events_position - 1]

    def new_event_count(self) -> int:
        return len(self.events) - self.new_events_position


class DoubleClient(AnyClient):
    def __init__(self, url: str, connection_kwargs, default_kwargs, session: Session = None):
        if session is None:
            session = Session()
        self.rst: Session = session
        if self.rst.prefix_url is None:
            self.rst.prefix_url = url
        self.sio: Client = Client(url, connection_kwargs, default_kwargs)

    def exit(self):
        self.rst.close()
        self.sio.disconnect()


class DoubleHClient(DoubleClient):
    def __init__(self, url: str, connection_kwargs, default_kwargs, session: Session = None):
        super().__init__(url, connection_kwargs, default_kwargs, session)
        self.sio: HClient = HClient(url, connection_kwargs, default_kwargs)

    def exit(self):
        self.rst.close()
        self.sio.disconnect()


class MultiClient:
    def __init__(self, server_url: str, **connect_kwargs: dict):
        self.connect_kwargs: dict = connect_kwargs
        self.server_url: str = server_url
        self.users: dict[str, AnyClient] = {}

    def __enter__(self):
        return self

    def connect_user(self, keep_history: bool = False, **connection_kwargs) -> AnyClient:
        if keep_history:
            return HClient(self.server_url, connection_kwargs, self.connect_kwargs)
        return Client(self.server_url, connection_kwargs, self.connect_kwargs)

    def attach_user(self, username: str, keep_history: bool = False, **connection_kwargs) -> None:
        self.users[username] = self.connect_user(keep_history, **connection_kwargs)

    def disconnect_user(self, username: str) -> None:
        self.users.pop(username).exit()

    def __exit__(self, exc_type, exc_val, exc_tb):
        for user in self.users.values():
            user.exit()
        self.users.clear()


class MultiDoubleClient(MultiClient):
    def connect_user(self, keep_history: bool = False, session: Session = None, **connection_kwargs) -> DoubleClient:
        if keep_history:
            return DoubleHClient(self.server_url, connection_kwargs, self.connect_kwargs, session)
        return DoubleClient(self.server_url, connection_kwargs, self.connect_kwargs, session)

    def attach_user(self, username: str, keep_history: bool = False, session: Session = None, **connection_kwargs):
        self.users[username] = self.connect_user(keep_history, session, **connection_kwargs)
