from pydantic import create_model, BaseModel, Field

from library import Session
from library0 import DuplexEvent, ServerEvent, ClientEvent, EventGroup
from setup import user_sessions
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
        chat_id = session.post(f"{self.host}/chat-temp/", json={"name": name}).json()["id"]
        self.add_chat.emit(f"user-{user_id}", chat_id=chat_id, name=name)

    @edit_chat.bind
    @user_sessions.with_request_session()
    def on_edit_chat(self, session: Session, chat_id: int, name: str):
        user_ids = get_participants(self.host, session, chat_id)
        session.put(f"{self.host}/chat-temp/{chat_id}/manage/", json={"name": name})
        users_broadcast(self.edit_chat, user_ids, chat_id=chat_id, name=name)

    @delete_chat.bind
    @user_sessions.with_request_session()
    def on_delete_chat(self, session: Session, chat_id: int):
        user_ids = get_participants(self.host, session, chat_id)
        session.delete(f"{self.host}/chat-temp/{chat_id}/manage/")
        users_broadcast(self.delete_chat, user_ids, chat_id=chat_id)
