from setup import socketio


def room_broadcast(event: str, data: dict, room: str, namespace: str = "/"):
    socketio.emit(event, data, to=room, namespace=namespace)
