from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Iterator
from urllib.parse import urljoin

from requests import Session as _Session
from socketio.client import Client as _Client


@dataclass()
class Event:
    name: str
    sid: str
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
        self.new_events_position: int = 0

    def exit(self):
        self.disconnect()

    def handler(self, event: str, sid: str, data: Any):
        self.events.append(Event(event, sid, data))

    def next_new_event(self) -> Optional[Event]:
        if self.new_events_position == len(self.events):
            return None
        self.new_events_position += 1
        return self.events[self.new_events_position - 1]

    def new_events(self) -> Iterator[Event]:
        while (new_event := self.next_new_event()) is not None:
            yield new_event

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


class MultiClient:
    def __init__(self, server_url: str, **connect_kwargs: dict):
        self.connect_kwargs: dict = connect_kwargs
        self.server_url: str = server_url
        self.users: dict[str, AnyClient] = {}

    def __enter__(self):
        return self

    def connect_user(self, **connection_kwargs) -> AnyClient:
        return Client(self.server_url, connection_kwargs, self.connect_kwargs)

    def attach_user(self, username: str, **connection_kwargs) -> None:
        self.users[username] = self.connect_user(**connection_kwargs)

    def disconnect_user(self, username: str) -> None:
        self.users.pop(username).exit()

    def __exit__(self, exc_type, exc_val, exc_tb):
        for user in self.users.values():
            user.exit()
        self.users.clear()


class MultiDoubleClient(MultiClient):
    def connect_user(self, base_session: Session = None, **connection_kwargs) -> DoubleClient:
        return DoubleClient(self.server_url, connection_kwargs, self.connect_kwargs, base_session)

    def attach_user(self, username: str, base_session: Session = None, **connection_kwargs) -> None:
        self.users[username] = self.connect_user(base_session, **connection_kwargs)
