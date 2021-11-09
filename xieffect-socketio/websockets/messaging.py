from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_socketio import join_room, leave_room, rooms

from setup import user_sessions, app
from .library import (room_broadcast, users_broadcast, Namespace,
                      with_arguments, EventArgument as EArg, with_request_session, Session)


def emit_notify(user_id: int, chat_id: int, unread: int):
    room_broadcast("notif", {"chat-id": chat_id, "unread": unread}, f"user-{user_id}")


def notify_offline(host: str, session: Session, chat_id: int) -> None:
    user_list = session.get(f"{host}/chat-temp/{chat_id}/users/offline/")
    for user_data in user_list.json():
        emit_notify(user_data["user-id"], chat_id, user_data["unread"])


def get_participants(host: str, session: Session, chat_id: int) -> list[int]:
    return session.get(f"{host}/chat-temp/{chat_id}/users/all/").json()


class MessagesNamespace(Namespace):
    def __init__(self, namespace=None):
        super().__init__(namespace)
        self.host = "http://localhost:5000" if app.debug else "https://xieffect.pythonanywhere.com"

    @jwt_required()  # if not self.authenticate(request.args): raise ConnectionRefusedError("unauthorized!")
    def on_connect(self, _):
        user_sessions.connect(get_jwt_identity())

    @with_request_session(use_user_id=True, ignore_errors=True)
    def on_disconnect(self, session: Session, user_id: int):
        user_sessions.disconnect(user_id)
        chat_ids = [int(chat_id) for room_name in rooms() if (chat_id := room_name.partition("chat-")[2]) != ""]
        session.post(f"{self.host}/chat-temp/close-all/", json={"ids": chat_ids})

    @with_request_session(use_user_id=True)
    @with_arguments(EArg("name"), use_original_data=False)
    def on_add_chat(self, session: Session, name: str, user_id: int):  # creates a new chat
        chat_id = session.post(f"{self.host}/chat-temp/", json={"name": name}).json()["id"]
        room_broadcast("add-chat", {"chat-id": chat_id, "name": name}, f"user-{user_id}")

    @with_request_session()
    @with_arguments(EArg("chat-id"), EArg("name"))
    def on_edit_chat(self, session: Session, chat_id: int, name: str, data: dict):
        user_ids = get_participants(self.host, session, chat_id)
        session.put(f"{self.host}/chat-temp/{chat_id}/manage/", json={"name": name})
        users_broadcast("edit-chat", data, user_ids)

    @with_request_session()
    @with_arguments(EArg("chat-id"))
    def on_delete_chat(self, session: Session, chat_id: int, data: dict):
        user_ids = get_participants(self.host, session, chat_id)
        session.delete(f"{self.host}/chat-temp/{chat_id}/manage/")
        users_broadcast("delete-chat", data, user_ids)

    @with_request_session()
    @with_arguments(EArg("chat-id"), EArg("user-ids"))
    def on_invite_users(self, session: Session, chat_id: int, user_ids: list[int], data: dict):
        # this does NOT check if invited users are already in the chat!
        session.post(f"{self.host}/chat-temp/{chat_id}/users/add-all/", json={"ids": user_ids})
        room_broadcast("invite-users", data, f"chat-{chat_id}")

        chat_name = session.get(f"{self.host}/chats/{chat_id}/").json()["name"]
        users_broadcast("add-chat", {"id": chat_id, "name": chat_name, "unread": 0}, user_ids)

    @with_request_session()
    @with_arguments(EArg("chat-id"), EArg("user-id"), EArg("role"))
    def on_invite_user(self, session: Session, chat_id: int, user_id: int, role: str, data: dict):
        # this does NOT check if invited user is already in the chat!
        session.post(f"{self.host}/chat-temp/{chat_id}/users/{user_id}/", json={"role": role})
        room_broadcast("invite-user", data, f"chat-{chat_id}")

        chat_name = session.get(f"{self.host}/chats/{chat_id}/").json()["name"]
        room_broadcast("add-chat", {"id": chat_id, "name": chat_name, "unread": 0}, f"user-{user_id}")

    @with_request_session()
    @with_arguments(EArg("chat-id"), EArg("user-id"), EArg("role"))
    def on_assign_user(self, session: Session, chat_id: int, user_id: int, role: str, data: dict):
        session.put(f"{self.host}/chat-temp/{chat_id}/users/{user_id}/", json={"role": role})
        room_broadcast("assign-user", data, f"chat-{chat_id}")

    @with_request_session(use_user_id=True)
    @with_arguments(EArg("chat-id"), EArg("user-id", dest="target_id"))
    def on_kick_user(self, session: Session, user_id: int, chat_id: int, target_id: int, data: dict):
        if user_id == target_id:  # quit
            session.delete(f"{self.host}/chat-temp/{chat_id}/membership/")
        else:  # kick
            session.delete(f"{self.host}/chat-temp/{chat_id}/users/{target_id}/")

        room_broadcast("kick-user", data, f"chat-{chat_id}")
        room_broadcast("delete-chat", {"id": chat_id}, f"user-{target_id}")
        # should remove user from room f"chat-{chat_id}"

    @with_request_session(use_user_id=True)
    @with_arguments(EArg("chat-id"), use_original_data=False)
    def on_open_chat(self, session: Session, chat_id: int, user_id: int):
        session.post(f"{self.host}/chat-temp/{chat_id}/presence/", json={"online": True})
        join_room(f"chat-{chat_id}")
        emit_notify(user_id, chat_id, 0)

    @with_request_session()
    @with_arguments(EArg("chat-id"), use_original_data=False)
    def on_close_chat(self, session: Session, chat_id: int):
        session.post(f"{self.host}/chat-temp/{chat_id}/presence/", json={"online": False})
        leave_room(f"chat-{chat_id}")

    @with_request_session()
    @with_arguments(EArg("chat-id"), EArg("content", check_only=True))
    def on_send_message(self, session: Session, chat_id: int, data: dict):
        session.post(f"{self.host}/chat-temp/{chat_id}/messages/", json=data)
        room_broadcast("send-message", data, f"chat-{chat_id}")
        notify_offline(self.host, session, chat_id)

    @with_request_session()
    @with_arguments(EArg("chat-id"), EArg("message-id"), EArg("content", check_only=True))
    def on_edit_message(self, session: Session, chat_id: int, message_id: int, data: dict):
        session.put(f"{self.host}/chat-temp/{chat_id}/messages/{message_id}/", json=data)
        room_broadcast("edit-message", data, f"chat-{chat_id}")
        notify_offline(self.host, session, chat_id)

    @with_request_session()
    @with_arguments(EArg("chat-id"), EArg("message-id"))
    def on_delete_message(self, session: Session, chat_id: int, message_id: int, data: dict):
        session.delete(f"{self.host}/chat-temp/{chat_id}/messages/{message_id}/")
        room_broadcast("delete-message", data, f"chat-{chat_id}")  # add "message" to data!!!
        notify_offline(self.host, session, chat_id)

# for user_data in data:
#     user_data["unread"] user_data["user-id"]
#     event_data.update({"chat-id": chat.id})
#     room_broadcast("notif", event_data, f"user-{user_id}")


# for user_id in user_ids:
#     room_broadcast(event, data, f"user-{user_id}")
