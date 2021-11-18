from typing import Union

from .library2 import SocketIOTestClient, Event


def assert_one(events: list[Event], data_only: bool = True) -> Union[Event, dict]:
    assert len(events) == 1, len(events)
    return events[0].data if data_only else events[0]


def assert_one_with_data(events: list[Event], data: dict):
    event_data = assert_one(events)
    assert event_data == data


def form_pass(method: str, url: str, req, res, code: int):
    return Event("pass", {"method": method, "url": url, "req": req, "res": res, "code": code})


def assert_broadcast(name: str, data: dict = None, *receivers: SocketIOTestClient):
    for receiver in receivers:
        event_data = assert_one(receiver.filter_received(name))
        assert event_data == data, (event_data, type(event_data), data, type(data))


def ensure_broadcast(sender: SocketIOTestClient, name: str, data: dict = None, *receivers: SocketIOTestClient,
                     include_self: bool = True) -> None:
    sender.emit(name, data)
    if include_self:
        receivers += (sender,)
    assert_broadcast(name, data, *receivers)


def ensure_pass(client: SocketIOTestClient, *passes: Event, include_get: bool = False):
    events = [event for event in client.filter_received("pass")
              if include_get or event.data.get("method", None) != "GET"]
    assert len(events) == len(passes), f"{len(events)=} {len(passes)=}"
    for i in range(len(passes)):
        event, pass_event = events[i], passes[i]
        assert event.data == pass_event.data


def assert_no_additional_messages(*clients):
    for i, client in enumerate(clients):
        assert len(client.get_received(keep_history=True)) == 0, (i, client.get_received())
