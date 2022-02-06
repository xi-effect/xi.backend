from __future__ import annotations

from typing import Union

from passlib.hash import pbkdf2_sha256
from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, Float, Text, JSON

from ._core import Base, sessionmaker
from .flask_fullstack import UserRole, create_marshal_model, Marshalable, LambdaFieldDef

DEFAULT_AVATAR: dict = {"accessory": 0, "body": 0, "face": 0, "hair": 0, "facialHair": 0, "bgcolor": 0}


class TokenBlockList(Base):
    __tablename__ = "token_block_list"

    id = Column(Integer, primary_key=True, unique=True)
    jti = Column(String(36), nullable=False)

    @classmethod
    def find_by_jti(cls, session: sessionmaker, jti) -> TokenBlockList:
        return session.execute(select(cls).where(cls.jti == jti)).scalars().first()

    @classmethod
    def add_by_jti(cls, session: sessionmaker, jti) -> None:
        session.add(cls(jti=jti))


@create_marshal_model("user-index", "username", "id", "bio", "avatar")
@create_marshal_model("profile", "name", "surname", "patronymic", "username",
                      "bio", "group", "avatar")
@create_marshal_model("full-settings", "email", "email_confirmed", "avatar", "code",
                      "name", "surname", "patronymic", "bio", "group", inherit="main-settings")
@create_marshal_model("main-settings", "id", "username", "dark_theme", "language")
@create_marshal_model("role-settings")
class User(Base, UserRole, Marshalable):
    __tablename__ = "users"
    not_found_text = "User does not exist"

    @staticmethod
    def generate_hash(password) -> str:
        return pbkdf2_sha256.hash(password)

    @staticmethod
    def verify_hash(password, hashed) -> bool:
        return pbkdf2_sha256.verify(password, hashed)

    # Vital:
    id = Column(Integer, primary_key=True)
    email = Column(String(100), nullable=False, unique=True)
    email_confirmed = Column(Boolean, nullable=False, default=False)
    password = Column(String(100), nullable=False)

    # Settings:
    username = Column(String(100), nullable=False)
    dark_theme = Column(Boolean, nullable=False, default=True)
    language = Column(String(20), nullable=False, default="russian")

    # profile:
    name = Column(String(100), nullable=True)
    surname = Column(String(100), nullable=True)
    patronymic = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    group = Column(String(100), nullable=True)
    avatar = Column(JSON, nullable=False, default=DEFAULT_AVATAR)

    # Education data:
    theory_level = Column(Float, nullable=False, default=0.5)
    filter_bind = Column(String(10), nullable=True)

    # Role-related:
    author = relationship("Author", backref="user", uselist=False)  # TODO remove non-common reference
    moderator = relationship("Moderator", backref="user", uselist=False)  # TODO remove non-common reference

    author_status: LambdaFieldDef = LambdaFieldDef("role-settings", str, lambda user: user.get_author_status())
    moderator_status: LambdaFieldDef = LambdaFieldDef("role-settings", bool, lambda user: user.moderator is not None)

    # Chat-related
    # chats = relationship("UserToChat", back_populates="user")  # TODO remove non-common reference

    # Invite-related
    code = Column(String(100), nullable=True)
    invite_id = Column(Integer, ForeignKey("invites.id"), nullable=True)  # TODO remove non-common reference
    invite = relationship("Invite", back_populates="invited")  # TODO remove non-common reference

    @classmethod
    def find_by_id(cls, session: sessionmaker, entry_id: int) -> Union[User, None]:
        return session.execute(select(cls).where(cls.id == entry_id)).scalars().first()

    @classmethod
    def find_by_email_address(cls, session: sessionmaker, email) -> Union[User, None]:
        # send_generated_email(email, "pass", "password-reset-email.html")
        return session.execute(select(cls).where(cls.email == email)).scalars().first()

    @classmethod  # TODO this class shouldn't know about invites
    def create(cls, session: sessionmaker, email: str, username: str, password: str, invite=None) -> Union[User, None]:
        if cls.find_by_email_address(session, email):
            return None
        new_user = cls(email=email, password=cls.generate_hash(password), username=username, invite=invite)
        session.add(new_user)
        session.flush()
        if invite is not None:
            new_user.code = new_user.invite.generate_code(new_user.id)
            session.flush()
        return new_user

    @classmethod
    def search_by_username(cls, session: sessionmaker, exclude_id: int, search: Union[str, None],
                           offset: int, limit: int) -> list[User]:
        stmt = select(cls).filter(cls.id != exclude_id)
        if search is not None:
            stmt = stmt.filter(cls.username.contains(search))
        return session.execute(stmt.offset(offset).limit(limit)).scalars().all()

    def change_email(self, session: sessionmaker, new_email: str) -> bool:
        if User.find_by_email_address(session, new_email):
            return False
        self.email = new_email
        self.email_confirmed = False
        return True

    def change_password(self, new_password: str) -> None:  # auto-commit
        self.password = User.generate_hash(new_password)

    def change_settings(self, new_values: dict[str, Union[str, int, bool]]) -> None:  # auto-commit  # TODO redo
        if "username" in new_values.keys():
            self.username = new_values["username"]
        if "dark-theme" in new_values.keys():
            self.dark_theme = new_values["dark-theme"]
        if "language" in new_values.keys():
            self.language = new_values["language"]
        if "name" in new_values.keys():
            self.name = new_values["name"]
        if "surname" in new_values.keys():
            self.surname = new_values["surname"]
        if "patronymic" in new_values.keys():
            self.patronymic = new_values["patronymic"]
        if "bio" in new_values.keys():
            self.bio = new_values["bio"]
        if "group" in new_values.keys():
            self.group = new_values["group"]
        if "avatar" in new_values.keys():
            self.avatar = new_values["avatar"]

    def get_author_status(self) -> str:
        return "not-yet" if self.author is None else "banned" if self.author.banned else "current"


UserRole.default_role = User
