from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Sequence, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, Text, DateTime, String, JSON
from sqlalchemy_enum34 import EnumType

from componets import create_marshal_model, Marshalable, LambdaFieldDef, TypeEnum
from componets.checkers import first_or_none, Identifiable
from main import Base, Session
from users import User


@create_marshal_model("message", "id", "content", "sender_id", "sent", "updated")
class Message(Base, Marshalable):
    __tablename__ = "messages"

    # Vital:
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), primary_key=True)
    chat = relationship("Chat", back_populates="messages")

    # Content related:
    content = Column(Text, nullable=False)

    # DateTime related:
    sent = Column(DateTime, nullable=False)
    updated = Column(DateTime, nullable=True)

    # Sender related:
    sender = relationship("User")
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    sender_name: LambdaFieldDef = LambdaFieldDef("message", str, lambda message: message.sender.username)
    sender_avatar: LambdaFieldDef = LambdaFieldDef("message", JSON, lambda message: message.sender.avatar)

    @classmethod
    def create(cls, session: Session, chat: Chat, content: str, sender: User) -> Message:
        entry: cls = cls(id=chat.get_next_message_id(), content=content,  # noqa
                         sent=datetime.utcnow(), sender=sender, chat=chat)  # noqa
        session.add(entry)
        session.flush()
        return entry

    @classmethod
    def find_by_ids(cls, session: Session, chat_id: int, message_id: int) -> Optional[Message]:
        return first_or_none(session.execute(select(cls).filter_by(chat_id=chat_id, id=message_id)).first())

    def delete(self, session: Session):
        session.delete(self)
        session.flush()


class ChatRole(TypeEnum):
    MUTED = 0  # get metadata, participants, messages
    BASIC = 1  # send, edit, delete own messages
    MODER = 2  # delete other's messages
    ADMIN = 3  # edit chat metadata, manage participants
    OWNER = 4  # delete the chat


@create_marshal_model("temp-u2c", "unread")
@create_marshal_model("user-in-chat", "role")
@create_marshal_model("chat-user-full", "role", inherit="chat-user-base")
@create_marshal_model("chat-user-index", inherit="chat-user-base")
@create_marshal_model("chat-user-base", "unread")
class UserToChat(Base, Marshalable):
    __tablename__ = "user_to_chat"
    _user_id2: LambdaFieldDef = LambdaFieldDef("temp-u2c", int, "user_id", "user-id")  # temp!!!

    # User-related
    user_id = Column(ForeignKey("users.id"), primary_key=True)
    user = relationship("User", back_populates="chats")

    _user_id: LambdaFieldDef = LambdaFieldDef("user-in-chat", int, "user_id", "id")
    username: LambdaFieldDef = LambdaFieldDef("user-in-chat", str, lambda u2c: u2c.user.username)
    user_avatar: LambdaFieldDef = LambdaFieldDef("user-in-chat", JSON, lambda u2c: u2c.user.avatar)

    # Chat-related
    chat_id = Column(ForeignKey("chats.id"), primary_key=True)
    chat = relationship("Chat")

    _chat_id: LambdaFieldDef = LambdaFieldDef("chat-user-index", int, "chat_id", "id")
    chat_name: LambdaFieldDef = LambdaFieldDef("chat-user-base", str, lambda u2c: u2c.chat.name, "name")
    chat_users: LambdaFieldDef = LambdaFieldDef("chat-user-full", int, lambda u2c: len(u2c.chat.participants), "users")

    # Other data:
    role = Column(EnumType(ChatRole, by_name=True), nullable=False, default="BASIC")
    online = Column(Integer, nullable=False, default=False)
    unread = Column(Integer, nullable=True)
    activity = Column(DateTime, nullable=True)

    @classmethod
    def find_by_ids(cls, session: Session, chat_id: int, user_id: int) -> UserToChat:
        return first_or_none(session.execute(select(cls).filter_by(chat_id=chat_id, user_id=user_id)))

    @classmethod
    def find_and_delete(cls, session: Session, chat_id: int, user_id: int) -> bool:
        if (entry := cls.find_by_ids(session, chat_id, user_id)) is None:
            return False
        entry.delete(session)
        return True

    @classmethod
    def find_by_user(cls, session: Session, user_id: int, offset: int, limit: int) -> list[UserToChat]:
        return session.execute(select(cls).filter_by(user_id=user_id).offset(offset).limit(limit)).scalars().all()

    @classmethod
    def find_and_close(cls, session: Session, user_id: int, chat_ids: list[int]) -> None:
        stmt = select(cls).filter(cls.user_id == user_id, cls.chat_id.in_(chat_ids), cls.online > 0)
        for user_to_chat in session.execute(stmt).scalars().all():
            user_to_chat.online -= 1

    @classmethod
    def find_by_chat(cls, session: Session, chat_id: int) -> list[UserToChat]:  # offline users only!
        stmt = select(cls).filter(cls.chat_id == chat_id, cls.online == 0)
        return session.execute(stmt).scalars().all()

    def delete(self, session: Session):
        session.delete(self)
        session.flush()


class Chat(Base, Marshalable, Identifiable):
    __tablename__ = "chats"
    not_found_text = "Chat not found"

    id = Column(Integer, Sequence("chat_id_seq"), primary_key=True)
    name = Column(String(100), nullable=False)

    messages = relationship("Message", back_populates="chat", cascade="all, delete", order_by=Message.id)
    participants = relationship("UserToChat", back_populates="chat", cascade="all, delete",
                                order_by=UserToChat.activity.desc())
    next_message_id = Column(Integer, nullable=False, default=0)

    @classmethod
    def create(cls, session: Session, name: str, owner: User) -> Chat:
        chat: cls = cls(name=name)
        owner.chats.append(UserToChat(chat=chat, role=ChatRole.OWNER))
        session.add(chat)
        session.flush()
        return chat

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> Optional[Chat]:
        return first_or_none(session.execute(select(cls).filter_by(id=entry_id)))

    def add_participant(self, user: User, role: ChatRole = ChatRole.BASIC) -> None:
        user.chats.append(UserToChat(chat=self, role=role))

    def get_next_message_id(self):
        self.next_message_id += 1
        return self.next_message_id

    def delete(self, session: Session):
        session.delete(self)
        session.flush()
