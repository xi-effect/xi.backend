from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Sequence, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, Text, DateTime, String
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

    @classmethod
    def create(cls, session: Session, chat: Chat, content: str, sender: User) -> Message:
        entry: cls = cls(content=content, sent=datetime.utcnow(), sender=sender, chat=chat)  # noqa
        session.add(entry)
        session.flush()
        return entry

    @classmethod
    def find_by_ids(cls, session: Session, chat_id: int, message_id: int) -> Optional[Message]:
        return first_or_none(session.execute(select(cls).filter_by(chat_id=chat_id, id=message_id)).first())

    def delete(self, session: Session):
        session.delete(self)
        session.flush()


@create_marshal_model("chat-full")
@create_marshal_model("chat-meta")
class Chat(Base, Marshalable, Identifiable):
    __tablename__ = "chats"
    not_found_text = "Chat not found"

    id = Column(Integer, Sequence("chat_id_seq"), primary_key=True)
    name = Column(String(100), nullable=False)

    messages = relationship("Message", back_populates="chat", cascade="all, delete", order_by=Message.id)
    participants = relationship("UserToChat", back_populates="chat")

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

    def add_participant(self, user: User) -> None:
        user.chats.append(UserToChat(chat=self, role=ChatRole.BASIC))

    def delete(self, session: Session):
        session.delete(self)
        session.flush()


class ChatRole(TypeEnum):
    MUTED = 0
    BASIC = 1
    MODER = 2
    ADMIN = 3
    OWNER = 4


@create_marshal_model("user2chat-full")
@create_marshal_model("user2chat-meta")
class UserToChat(Base, Marshalable):
    __tablename__ = "chat_to_user"

    user_id = Column(ForeignKey("users.id"), primary_key=True)
    chat_id = Column(ForeignKey("chats.id"), primary_key=True)
    chat = relationship("Chat")

    role = Column(EnumType(ChatRole, by_name=True), nullable=False, default="BASIC")
    unread = Column(Integer, nullable=True)

    @classmethod
    def find_by_ids(cls, session: Session, chat_id: int, user_id: int) -> UserToChat:
        return first_or_none(session.execute(select(cls).filter_by(chat_id=chat_id, user_id=user_id)))

    @classmethod
    def find_and_delete(cls, session: Session, chat_id: int, user_id: int) -> bool:
        if (entry := cls.find_by_ids(session, chat_id, user_id)) is None:
            return False
        entry.delete(session)
        return True

    def delete(self, session: Session):
        session.delete(self)
        session.flush()
