from requests import post

from main import app


def broadcast(event: str, data: dict, *user_ids: int):
    host = "http://localhost:5050" if app.debug else "https://xieffect-socketio.herokuapp.com"
    post(f"{host}/pass-through/broadcast/{event}/",
         json={"user_ids": user_ids, "data": data})
