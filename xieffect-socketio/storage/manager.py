from flask import request
from flask_socketio import join_room, close_room
from websockets import Session


class UserSession:
    def __init__(self):
        self.sessions: dict[int, Session] = dict()
        self.counters: dict[int, int] = dict()

    def connect(self, user_id: int):
        if user_id in self.sessions.keys():
            self.sessions[user_id] = Session()
            self.sessions[user_id].cookies.set("access_token_cookie", request.cookies["access_token_cookie"])
            self.counters[user_id] = 1
        else:
            self.counters[user_id] += 1
        join_room(f"user-{user_id}")

    def disconnect(self, user_id: int):
        self.counters[user_id] -= 1
        if self.counters[user_id] == 0:
            self.sessions.pop(user_id)
            self.counters.pop(user_id)
            close_room(f"user-{user_id}")
