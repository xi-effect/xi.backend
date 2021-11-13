from pydantic import create_model, BaseModel, Field

from library import Session
from library0 import DuplexEvent, ServerEvent, ClientEvent, EventGroup
from setup import user_sessions, app
from .library import users_broadcast


def get_participants(host: str, session: Session, chat_id: int) -> list[int]:
    return session.get(f"{host}/chat-temp/{chat_id}/users/all/").json()


class ChatMeta(BaseModel):
    chat_id: int = Field(alias="chat-id")
    name: str


class ChatManagement(EventGroup):
    add_chat: DuplexEvent = DuplexEvent(ClientEvent(create_model("ChatName", name=(str, ...))), ServerEvent(ChatMeta))
    edit_chat: DuplexEvent = DuplexEvent.similar(ChatMeta)
    delete_chat: DuplexEvent = DuplexEvent.similar(create_model("ChatID", chat_id=(int, ...)))

    @add_chat.bind
    @user_sessions.with_request_session(use_user_id=True)
    def on_add_chat(self, session: Session, name: str, user_id: int):
        chat_id = session.post(f"{app.config['host']}/chat-temp/", json={"name": name}).json()["id"]
        self.add_chat.emit(f"user-{user_id}", chat_id=chat_id, name=name)

    @edit_chat.bind
    @user_sessions.with_request_session()
    def on_edit_chat(self, session: Session, chat_id: int, name: str):
        user_ids = get_participants(app.config['host'], session, chat_id)
        session.put(f"{app.config['host']}/chat-temp/{chat_id}/manage/", json={"name": name})
        users_broadcast(self.edit_chat, user_ids, chat_id=chat_id, name=name)

    @delete_chat.bind
    @user_sessions.with_request_session()
    def on_delete_chat(self, session: Session, chat_id: int):
        user_ids = get_participants(app.config['host'], session, chat_id)
        session.delete(f"{app.config['host']}/chat-temp/{chat_id}/manage/")
        users_broadcast(self.delete_chat, user_ids, chat_id=chat_id)


class UserToChat(BaseModel):
    chat_id: int = Field(alias="chat-id")
    target_id: int = Field(alias="user-id")


class UserToChatWithRole(UserToChat):
    role: str


class ChatUserManagement(EventGroup):
    invite_users = DuplexEvent.similar(create_model("InviteUsers", chat_id=(int, ...), user_ids=(list[int], ...)))
    invite_user = DuplexEvent.similar(UserToChatWithRole)
    assign_user = DuplexEvent.similar(UserToChatWithRole)
    kick_user = DuplexEvent.similar(UserToChat)

    @invite_users.bind
    @user_sessions.with_request_session()
    def on_invite_users(self, session: Session, chat_id: int, user_ids: list[int]):
        # this does NOT check if invited users are already in the chat!
        session.post(f"{app.config['host']}/chat-temp/{chat_id}/users/add-all/", json={"ids": user_ids})
        self.invite_users.emit(f"chat-{chat_id}", chat_id=chat_id, user_ids=user_ids)

        chat_name = session.get(f"{app.config['host']}/chats/{chat_id}/").json()["name"]
        users_broadcast(ChatManagement.add_chat, user_ids, chat_id=chat_id, name=chat_name)

    @invite_user.bind
    @user_sessions.with_request_session()
    def on_invite_user(self, session: Session, chat_id: int, target_id: int, role: str):
        # this does NOT check if invited user is already in the chat!
        session.post(f"{app.config['host']}/chat-temp/{chat_id}/users/{target_id}/", json={"role": role})
        self.invite_user.emit(f"chat-{chat_id}", chat_id=chat_id, target_id=target_id, role=role)

        chat_name = session.get(f"{app.config['host']}/chats/{chat_id}/").json()["name"]
        ChatManagement.add_chat.emit(f"user-{target_id}", chat_id=chat_id, name=chat_name)

    @assign_user.bind
    @user_sessions.with_request_session()
    def on_assign_user(self, session: Session, chat_id: int, target_id: int, role: str):
        session.put(f"{app.config['host']}/chat-temp/{chat_id}/users/{target_id}/", json={"role": role})
        self.assign_user.emit(f"chat-{chat_id}", chat_id=chat_id, target_id=target_id, role=role)

    @kick_user.bind
    @user_sessions.with_request_session(use_user_id=True)
    def on_kick_user(self, session: Session, user_id: int, chat_id: int, target_id: int):
        if user_id == target_id:  # quit
            session.delete(f"{app.config['host']}/chat-temp/{chat_id}/membership/")
        else:  # kick
            session.delete(f"{app.config['host']}/chat-temp/{chat_id}/users/{target_id}/")

        self.kick_user.emit(f"chat-{chat_id}", chat_id=chat_id, target_id=target_id)
        ChatManagement.delete_chat.emit(f"user-{target_id}", chat_id=chat_id)
        # should remove user from room f"chat-{chat_id}"
