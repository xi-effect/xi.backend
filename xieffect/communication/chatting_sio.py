from flask_socketio import leave_room
from pydantic import create_model, BaseModel, Field

from common import users_broadcast, DuplexEvent, ServerEvent, ClientEvent, EventGroup, User, with_session
from .chatting_db import Chat, ChatRole, UserToChat


def get_participants(session, chat_id: int) -> list[int]:
    chat: Chat = Chat.find_by_id(session, chat_id)  # TODO errors
    return [u2c.user_id for u2c in chat.participants]


class ChatMeta(BaseModel):
    chat_id: int = Field(alias="chat-id")
    name: str


add_chat: DuplexEvent = DuplexEvent(ClientEvent(create_model("ChatName", name=(str, ...))), ServerEvent(ChatMeta))
edit_chat: DuplexEvent = DuplexEvent.similar(ChatMeta)
delete_chat: DuplexEvent = DuplexEvent.similar(create_model("ChatID", chat_id=(int, ...)))


# TODO user_id should appear there somehow

@add_chat.bind
@with_session
def on_add_chat(session, name: str, user_id: int):
    user: User = User.find_by_id(session, user_id)  # TODO errors
    chat_id = Chat.create(session, name, user).id  # TODO errors
    add_chat.emit(f"user-{user_id}", chat_id=chat_id, name=name)


@edit_chat.bind
@with_session
def on_edit_chat(session, chat_id: int, name: str):
    user_ids = get_participants(session, chat_id)

    chat = Chat.find_by_id(session, chat_id)  # TODO errors
    # TODO min_role=ChatRole.ADMIN
    chat.name = name

    users_broadcast(edit_chat, user_ids, chat_id=chat_id, name=name)


@delete_chat.bind
@with_session
def on_delete_chat(session, chat_id: int):
    user_ids = get_participants(session, chat_id)

    chat = Chat.find_by_id(session, chat_id)  # TODO errors
    # TODO min_role=ChatRole.OWNER
    chat.delete(session)

    users_broadcast(delete_chat, user_ids, chat_id=chat_id)


# MEMBER MANAGEMENT #

class UserAndChat(BaseModel):
    chat_id: int = Field(alias="chat-id")
    target_id: int = Field(alias="user-id")


class UserAndChatWithRole(UserAndChat):
    role: str


invite_users = DuplexEvent.similar(create_model("InviteUsers", chat_id=(int, ...), user_ids=(list[int], ...)))
invite_user = DuplexEvent.similar(UserAndChatWithRole)
assign_user = DuplexEvent.similar(UserAndChatWithRole)
kick_user = DuplexEvent.similar(create_model("KickUser", chat_id=(int, ...), target_id=(int, None)))
assign_owner = DuplexEvent(ClientEvent(UserAndChat),
                           ServerEvent(create_model("Transfer", __base__=UserAndChat, source_id=(int, None))))


def add_chat_participant(session, user_id: int, chat: Chat) -> bool:
    return (user := User.find_by_id(session, user_id) is not None) and chat.add_participant(session, user)


@invite_users.bind
@with_session
def on_invite_users(session, chat_id: int, user_ids: list[int]):
    chat = Chat.find_by_id(session, chat_id)  # TODO errors
    # TODO min_role=ChatRole.ADMIN
    user_ids = [user_id for user_id in user_ids if add_chat_participant(session, user_id, chat)]

    if len(user_ids) > 0:
        invite_users.emit(f"chat-{chat_id}", chat_id=chat_id, user_ids=user_ids)
        users_broadcast(add_chat, user_ids, chat_id=chat_id, name=chat.name)


@invite_user.bind
@with_session
def on_invite_user(session, chat_id: int, target_id: int, role: str):
    chat: Chat = Chat.find_by_id(session, chat_id)  # TODO errors
    # TODO min_role=ChatRole.ADMIN

    try:
        role: ChatRole = ChatRole.BASIC if role is None else ChatRole.from_string(role)
    except (ValueError, KeyError):
        pass  # TODO errors

    if chat.add_participant(session, User.find_by_id(session, target_id), role):
        invite_user.emit(f"chat-{chat_id}", chat_id=chat_id, target_id=target_id, role=role)
        add_chat.emit(f"user-{target_id}", chat_id=chat_id, name=chat.name)


@assign_user.bind
@with_session
def on_assign_user(session, chat_id: int, target_id: int, role: str):
    target_to_chat: UserToChat = UserToChat.find_by_ids(session, chat_id, target_id)  # TODO errors
    # TODO min_role=ChatRole.MODER
    # TODO user.role > role & user.role > target_to_chat.role

    if target_to_chat.role != role:
        target_to_chat.role = role
        assign_user.emit(f"chat-{chat_id}", chat_id=chat_id, target_id=target_id, role=role)


def emit_user_kick(chat_id: int, target_id: int):
    kick_user.emit(f"chat-{chat_id}", chat_id=chat_id, target_id=target_id)
    delete_chat.emit(f"user-{target_id}", chat_id=chat_id)
    # should remove user from room f"chat-{chat_id}"


@kick_user.bind
@with_session
def on_kick_user(session, user_id: int, chat_id: int, target_id: int = None):
    if target_id is not None and user_id != target_id:  # kick
        target_to_chat: UserToChat = UserToChat.find_by_ids(session, chat_id, target_id)  # TODO errors
        # TODO min_role=ChatRole.ADMIN
        # TODO user.role > role & user.role > target_to_chat.role
        target_to_chat.delete(session)
        emit_user_kick(chat_id, target_id)
        return

    # quit
    leave_room(f"chat-{chat_id}")
    user_to_chat: UserToChat = UserToChat.find_by_ids(session, chat_id, user_id)  # TODO errors
    user_to_chat.delete(session)
    if user_to_chat.role is ChatRole.OWNER:  # Automatic ownership transfer
        if (successor := UserToChat.find_successor(session, user_to_chat.chat_id)) is None:
            Chat.find_by_id(session, user_to_chat.chat_id).delete(session)
            delete_chat.emit(f"user-{user_id}", chat_id=chat_id)  # chat is deleted
            return
        successor.role = ChatRole.OWNER
        assign_owner.emit(f"chat-{chat_id}", chat_id=chat_id, target_id=successor.id)
    emit_user_kick(chat_id, user_id)


@assign_owner.bind
@with_session
def on_assign_owner(session, user_id: int, chat_id: int, target_id: int):
    # TODO min_role=ChatRole.OWNER
    user_to_chat: UserToChat = UserToChat.find_by_ids(session, chat_id, user_id)  # TODO errors
    target_to_chat: UserToChat = UserToChat.find_by_ids(session, chat_id, target_id)  # TODO errors

    user_to_chat.role = ChatRole.ADMIN
    target_to_chat.role = ChatRole.OWNER

    assign_owner.emit(f"chat-{chat_id}", chat_id=chat_id, target_id=target_id, source_id=user_id)


chat_management_events: EventGroup = EventGroup(add_chat=add_chat, edit_chat=edit_chat, delete_chat=delete_chat)
user_management_events: EventGroup = EventGroup(invite_users=invite_users, invite_user=invite_user,
                                                assign_user=assign_user, kick_user=kick_user, assign_owner=assign_owner)
