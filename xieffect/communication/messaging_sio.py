from datetime import datetime

from flask_socketio import join_room, leave_room
from pydantic import create_model

from common import EventGroup, ServerEvent, ClientEvent, DuplexEvent, with_session, User
from .chatting_db import UserToChat, Chat, Message

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

# TODO user_id should appear there somehow


@open_chat.bind
@with_session
def on_open_chat(session, chat_id: int, user_id: int):
    user_to_chat: UserToChat = UserToChat.find_by_ids(session, chat_id, user_id)  # TODO errors
    user_to_chat.online += 1

    join_room(f"chat-{chat_id}")

    if user_to_chat.online == 1 and user_to_chat.unread != 0:
        user_to_chat.unread = 0
        notif.emit(f"user-{user_id}", chat_id=chat_id, unread=0)


@close_chat.bind
@with_session
def on_close_chat(session, chat_id: int, user_id: int, kicked: bool = False):
    if not kicked:  # kostil & security flaw!
        user_to_chat: UserToChat = UserToChat.find_by_ids(session, chat_id, user_id)  # TODO errors
        user_to_chat.online += -1
    leave_room(f"chat-{chat_id}")


@send_message.bind
@with_session
def on_send_message(session, chat_id: int, user_id: int, content: str):
    chat = Chat.find_by_id(session, chat_id)  # TODO errors
    user_to_chat: UserToChat = UserToChat.find_by_ids(session, chat_id, user_id)  # TODO errors
    user: User = User.find_by_id(session, user_id)  # TODO errors
    # TODO min_role=BASIC

    message = Message.create(session, chat, content, user)  # TODO errors
    user_to_chat.activity = message.sent
    send_message.emit(f"chat-{chat_id}", chat_id=chat_id, content=content, message_id=message.id, sent=message.sent)

    for u2c in UserToChat.find_by_chat(session, chat.id):
        notif.emit("user-" + str(u2c.user_id), chat_id=chat_id, unread=u2c.unread)


@edit_message.bind
@with_session
def on_edit_message(session, chat_id: int, message_id: int, content: str):
    message: Message = Message.find_by_ids(session, chat_id, message_id)  # TODO errors
    # TODO min_role=BASIC & your message

    message.content = content
    message.updated = datetime.utcnow()
    edit_message.emit(f"chat-{chat_id}", chat_id=chat_id, message_id=message_id, content=content, updated=message.updated)


@delete_message.bind
def on_delete_message(session, chat_id: int, message_id: int):
    # TODO role > MODER || (min_role=BASIC & your message)
    Message.find_by_ids(session, chat_id, message_id).delete(session)  # TODO errors
    delete_message.emit(f"chat-{chat_id}", chat_id=chat_id, message_id=message_id)


messaging_events: EventGroup = EventGroup(notif=notif, open_chat=open_chat, close_chat=close_chat,
                                          send_message=send_message, edit_message=edit_message,
                                          delete_message=delete_message)
