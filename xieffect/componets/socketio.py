from requests import post

from main import app


def broadcast(event: str, data: dict, *user_ids: int):
    host = "http://localhost:5050" if app.debug else "https://xieffect-socketio.herokuapp.com"
    post(f"{host}/broadcast/{event}/",
         json={"user_ids": user_ids, "data": data})


def room_broadcast(event: str, data: dict, room: str, namespace: str = "/"):
    host = "http://localhost:5050" if app.debug else "https://xieffect-socketio.herokuapp.com"
    post(f"{host}/broadcast/{event}/rooms/{room}/",
         json={"data": data, "namespace": namespace})
