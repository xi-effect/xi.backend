from flask_socketio import leave_room
from pydantic import create_model, BaseModel, Field

from library import Session, users_broadcast
from library0 import DuplexEvent, ServerEvent, ClientEvent, EventGroup
from setup import user_sessions, app


def get_participants(host: str, session: Session, chat_id: int) -> list[int]:
    return session.get(f"{host}/chat-temp/{chat_id}/users/all/").json()


class ChatMeta(BaseModel):
    chat_id: int = Field(alias="chat-id")
    name: str


add_chat: DuplexEvent = DuplexEvent(ClientEvent(create_model("ChatName", name=(str, ...))), ServerEvent(ChatMeta))
edit_chat: DuplexEvent = DuplexEvent.similar(ChatMeta)
delete_chat: DuplexEvent = DuplexEvent.similar(create_model("ChatID", chat_id=(int, ...)))


@add_chat.bind
@user_sessions.with_request_session(use_user_id=True)
def on_add_chat(session: Session, name: str, user_id: int):
    chat_id = session.post(f"{app.config['host']}/chat-temp/", json={"name": name}).json()["id"]
    add_chat.emit(f"user-{user_id}", chat_id=chat_id, name=name)


@edit_chat.bind
@user_sessions.with_request_session()
def on_edit_chat(session: Session, chat_id: int, name: str):
    user_ids = get_participants(app.config['host'], session, chat_id)
    session.put(f"{app.config['host']}/chat-temp/{chat_id}/manage/", json={"name": name})
    users_broadcast(edit_chat, user_ids, chat_id=chat_id, name=name)


@delete_chat.bind
@user_sessions.with_request_session()
def on_delete_chat(session: Session, chat_id: int):
    user_ids = get_participants(app.config['host'], session, chat_id)
    session.delete(f"{app.config['host']}/chat-temp/{chat_id}/manage/")
    users_broadcast(delete_chat, user_ids, chat_id=chat_id)


class UserToChat(BaseModel):
    chat_id: int = Field(alias="chat-id")
    target_id: int = Field(alias="user-id")


class UserToChatWithRole(UserToChat):
    role: str


invite_users = DuplexEvent.similar(create_model("InviteUsers", chat_id=(int, ...), user_ids=(list[int], ...)))
invite_user = DuplexEvent.similar(UserToChatWithRole)
assign_user = DuplexEvent.similar(UserToChatWithRole)
kick_user = DuplexEvent.similar(create_model("KickUser", chat_id=(int, ...), target_id=(int, None)))
assign_owner = DuplexEvent(ClientEvent(UserToChat),
                           ServerEvent(create_model("Transfer", __base__=UserToChat, source_id=(int, None))))


@invite_users.bind
@user_sessions.with_request_session()
def on_invite_users(session: Session, chat_id: int, user_ids: list[int]):
    r = session.post(f"{app.config['host']}/chat-temp/{chat_id}/users/add-all/", json={"ids": user_ids}).json()
    user_ids = [user_ids[i] for i in range(len(user_ids)) if r[i]]

    if len(user_ids) > 0:
        invite_users.emit(f"chat-{chat_id}", chat_id=chat_id, user_ids=user_ids)
        chat_name = session.get(f"{app.config['host']}/chats/{chat_id}/").json()["name"]
        users_broadcast(add_chat, user_ids, chat_id=chat_id, name=chat_name)


@invite_user.bind
@user_sessions.with_request_session()
def on_invite_user(session: Session, chat_id: int, target_id: int, role: str):
    if session.post(f"{app.config['host']}/chat-temp/{chat_id}/users/{target_id}/", json={"role": role}).json()["a"]:
        invite_user.emit(f"chat-{chat_id}", chat_id=chat_id, target_id=target_id, role=role)

        chat_name = session.get(f"{app.config['host']}/chats/{chat_id}/").json()["name"]
        add_chat.emit(f"user-{target_id}", chat_id=chat_id, name=chat_name)


@assign_user.bind
@user_sessions.with_request_session()
def on_assign_user(session: Session, chat_id: int, target_id: int, role: str):
    if session.put(f"{app.config['host']}/chat-temp/{chat_id}/users/{target_id}/", json={"role": role}).json()["a"]:
        assign_user.emit(f"chat-{chat_id}", chat_id=chat_id, target_id=target_id, role=role)


def emit_user_kick(chat_id: int, target_id: int):
    kick_user.emit(f"chat-{chat_id}", chat_id=chat_id, target_id=target_id)
    delete_chat.emit(f"user-{target_id}", chat_id=chat_id)
    # should remove user from room f"chat-{chat_id}"


@kick_user.bind
@user_sessions.with_request_session(use_user_id=True)
def on_kick_user(session: Session, user_id: int, chat_id: int, target_id: int = None):
    if target_id is not None and user_id != target_id:  # kick
        session.delete(f"{app.config['host']}/chat-temp/{chat_id}/users/{target_id}/")
        emit_user_kick(chat_id, target_id)
        return
    # quit
    res = session.delete(f"{app.config['host']}/chat-temp/{chat_id}/membership/").json()
    leave_room(f"chat-{chat_id}")
    if res["branch"] == "delete-chat":
        delete_chat.emit(f"user-{user_id}", chat_id=chat_id)  # chat is deleted
    elif res["branch"] == "assign-owner":
        emit_user_kick(chat_id, user_id)
        assign_owner.emit(f"chat-{chat_id}", chat_id=chat_id, target_id=res["successor"])
    else:
        emit_user_kick(chat_id, user_id)


@assign_owner.bind
@user_sessions.with_request_session(use_user_id=True)
def on_assign_owner(session: Session, user_id: int, chat_id: int, target_id: int):
    session.post(f"{app.config['host']}/chat-temp/{chat_id}/users/{target_id}/owner/")
    assign_owner.emit(f"chat-{chat_id}", chat_id=chat_id, target_id=target_id, source_id=user_id)


chat_management_events: EventGroup = EventGroup(add_chat=add_chat, edit_chat=edit_chat, delete_chat=delete_chat)
user_management_events: EventGroup = EventGroup(invite_users=invite_users, invite_user=invite_user,
                                                assign_user=assign_user, kick_user=kick_user, assign_owner=assign_owner)
