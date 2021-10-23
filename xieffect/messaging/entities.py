from __future__ import annotations

from sqlalchemy import Column, Sequence, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, Text, DateTime, String
from sqlalchemy_enum34 import EnumType

from componets import create_marshal_model, Marshalable, LambdaFieldDef, TypeEnum
from componets.checkers import first_or_none
from main import Base, Session
from users import User


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

    @classmethod
    def create(cls, session: Session) -> Message:
        pass


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, Sequence("chat_id_seq"), primary_key=True)
    name = Column(String(100), nullable=False)

    messages = relationship("Message", back_populates="chat", cascade="all, delete", order_by=Message.id)
    participants = relationship("UserToChat", back_populates="chat")

    @classmethod
    def create(cls, session: Session, name: str, owner: User) -> Chat:
        pass


class ChatRole(TypeEnum):
    BASIC = 0
    ADMIN = 1
    OWNER = 2


class UserToChat(Base):
    __tablename__ = "chat_to_user"

    user_id = Column(ForeignKey("users.id"), primary_key=True)
    chat_id = Column(ForeignKey("chats.id"), primary_key=True)
    chat = relationship("Chat")

    role = Column(EnumType(ChatRole, by_name=True), nullable=False, default="BASIC")
    unread = Column(Integer, nullable=True)
