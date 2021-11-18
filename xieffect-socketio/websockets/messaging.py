from flask_socketio import join_room, leave_room
from pydantic import create_model

from library import Session
from library0 import EventGroup, ServerEvent, ClientEvent, DuplexEvent
from setup import user_sessions, app

create_message_i_model = create_model("NewMessageI", chat_id=(int, ...), content=(str, ...))
edit_message_i_model = create_model("EditMessageI", __base__=create_message_i_model, message_id=(int, ...))
create_message_o_model = create_model("NewMessageO", __base__=edit_message_i_model, sent=(str, ...))
edit_message_o_model = create_model("EditMessageO", __base__=edit_message_i_model, updated=(str, ...))
delete_message_model = create_model("DeleteMessage", chat_id=(int, ...), message_id=(int, ...))

notif: ServerEvent = ServerEvent(create_model("Notif", chat_id=(int, ...), unread=0))
open_chat: ClientEvent = ClientEvent(create_model("ChatID", chat_id=(int, ...)))
close_chat: ClientEvent = ClientEvent(create_model("ChatID", chat_id=(int, ...), kicked=False))

send_message: DuplexEvent = DuplexEvent(ClientEvent(create_message_i_model), ServerEvent(create_message_o_model))
edit_message: DuplexEvent = DuplexEvent(ClientEvent(edit_message_i_model), ServerEvent(edit_message_o_model))
delete_message: DuplexEvent = DuplexEvent.similar(delete_message_model)


def notify_offline(session: Session, chat_id: int) -> None:
    user_list = session.get(f"{app.config['host']}/chat-temp/{chat_id}/users/offline/")
    for user_data in user_list.json():
        notif.emit("user-" + str(user_data["user-id"]), chat_id=chat_id, unread=user_data["unread"])


@open_chat.bind
@user_sessions.with_request_session(use_user_id=True)
def on_open_chat(session: Session, chat_id: int, user_id: int):
    notify_needed = session.post(
        f"{app.config['host']}/chat-temp/{chat_id}/presence/", json={"online": True}).json()["a"]
    join_room(f"chat-{chat_id}")
    if notify_needed:
        notif.emit(f"user-{user_id}", chat_id=chat_id, unread=0)


@close_chat.bind
@user_sessions.with_request_session()
def on_close_chat(session: Session, chat_id: int, kicked: bool = False):
    if not kicked:  # kostil & security flaw!
        session.post(f"{app.config['host']}/chat-temp/{chat_id}/presence/", json={"online": False})
    leave_room(f"chat-{chat_id}")


@send_message.bind
@user_sessions.with_request_session()
def on_send_message(session: Session, chat_id: int, content: str):
    json = {"chat-id": chat_id, "content": content}
    message_data = session.post(f"{app.config['host']}/chat-temp/{chat_id}/messages/", json=json).json()
    send_message.emit(f"chat-{chat_id}", chat_id=chat_id, content=content, **message_data)
    notify_offline(session, chat_id)


@edit_message.bind
@user_sessions.with_request_session()
def on_edit_message(session: Session, chat_id: int, message_id: int, content: str):
    updated = session.put(f"{app.config['host']}/chat-temp/{chat_id}/messages/{message_id}/",
                          json={"chat-id": chat_id, "content": content, "message-id": message_id}).json()["updated"]
    edit_message.emit(f"chat-{chat_id}", chat_id=chat_id, message_id=message_id, content=content, updated=updated)


@delete_message.bind
@user_sessions.with_request_session()
def on_delete_message(session: Session, chat_id: int, message_id: int):
    session.delete(f"{app.config['host']}/chat-temp/{chat_id}/messages/{message_id}/")
    delete_message.emit(f"chat-{chat_id}", chat_id=chat_id, message_id=message_id)
    notify_offline(session, chat_id)


messaging_events: EventGroup = EventGroup(notif=notif, open_chat=open_chat, close_chat=close_chat,
                                          send_message=send_message, edit_message=edit_message,
                                          delete_message=delete_message)
