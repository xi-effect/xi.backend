from __future__ import annotations

from typing import Optional

from sqlalchemy import Column, Sequence, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, Text, DateTime, String
from sqlalchemy_enum34 import EnumType

from componets import create_marshal_model, Marshalable, LambdaFieldDef, TypeEnum
from componets.checkers import first_or_none, Identifiable
from main import Base, Session
from users import User


@create_marshal_model("message-full", inherit="message-base")
@create_marshal_model("message-base", )
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

    sender_name = LambdaFieldDef("message-base", str, lambda message: message.sender.username)

    @classmethod
    def create(cls, session: Session) -> Message:
        pass


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
        pass

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> Optional[Chat]:
        pass


class ChatRole(TypeEnum):
    BASIC = 0
    ADMIN = 1
    OWNER = 2


@create_marshal_model("user2chat-full")
@create_marshal_model("user2chat-meta")
class UserToChat(Base, Marshalable):
    __tablename__ = "chat_to_user"

    user_id = Column(ForeignKey("users.id"), primary_key=True)
    chat_id = Column(ForeignKey("chats.id"), primary_key=True)
    chat = relationship("Chat")

    role = Column(EnumType(ChatRole, by_name=True), nullable=False, default="BASIC")
    unread = Column(Integer, nullable=True)
