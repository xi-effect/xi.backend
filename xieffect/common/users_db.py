from __future__ import annotations

from collections.abc import Callable

from passlib.hash import pbkdf2_sha256
from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, Float, Text, JSON

from __lib__.flask_fullstack import UserRole, PydanticModel, Identifiable
from . import Base, sessionmaker

DEFAULT_AVATAR: dict = {
    "topType": 0,
    "accessoriesType": 0,
    "hairColor": 0,
    "facialHairType": 0,
    "clotheType": 0,
    "eyeType": 0,
    "eyebrowType": 0,
    "mouthType": 0,
    "skinColor": 0,
    "bgcolor": 0,
}


class BlockedToken(Base):
    __tablename__ = "blocked_tokens"

    id = Column(Integer, primary_key=True, unique=True)
    jti = Column(String(36), nullable=False)

    @classmethod
    def find_by_jti(cls, session: sessionmaker, jti: str) -> BlockedToken:
        return session.get_first(select(cls).filter_by(jti=jti))


class User(Base, UserRole, Identifiable):
    __tablename__ = "users"
    not_found_text = "User does not exist"
    unauthorized_error = (401, not_found_text)

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
    author = relationship("Author", backref="user", uselist=False)
    # TODO remove non-common reference
    # moderator = relationship("Moderator", backref="user", uselist=False)  # TODO DEPRECATED, redo with MUB

    # Chat-related
    # chats = relationship("UserToChat", back_populates="user")  # TODO remove non-common reference

    # Invite-related
    code = Column(String(100), nullable=True)
    invite_id = Column(Integer, ForeignKey("invites.id"), nullable=True)
    # TODO remove non-common reference
    invite = relationship(
        "Invite", back_populates="invited"
    )  # TODO remove non-common reference

    IndexProfile = PydanticModel.column_model(id, username, bio, avatar)
    FullProfile = IndexProfile.column_model(name, surname, patronymic, group)

    MainData = PydanticModel.column_model(id, username, dark_theme, language, avatar)
    FullData = MainData.column_model(
        email, email_confirmed, avatar, code, name, surname, patronymic, bio, group
    )

    class RoleSettings(PydanticModel):
        author_status: str
        moderator_status: bool

        @classmethod
        def callback_convert(cls, callback: Callable, orm_object: User, **_) -> None:
            callback(
                author_status=orm_object.get_author_status(),
                moderator_status=orm_object.moderator is not None,
            )

    @classmethod
    def find_by_id(cls, session: sessionmaker, entry_id: int) -> User | None:
        return session.get_first(select(cls).filter_by(id=entry_id))

    @classmethod
    def find_by_identity(cls, session, identity: int) -> User | None:
        return cls.find_by_id(session, identity)

    @classmethod
    def find_by_email_address(cls, session: sessionmaker, email) -> User | None:
        return session.get_first(select(cls).filter_by(email=email))

    @classmethod  # TODO this class shouldn't know about invites
    def create(
        cls, session: sessionmaker, *, email: str, password: str, invite=None, **kwargs
    ) -> User | None:
        if cls.find_by_email_address(session, email):
            return None
        new_user = super().create(
            session,
            email=email,
            password=cls.generate_hash(password),
            invite=invite,
            **kwargs,
        )
        if invite is not None:
            new_user.code = new_user.invite.generate_code(new_user.id)
            session.flush()
        return new_user

    @classmethod
    def search_by_params(cls, session, offset: int, limit: int, **kwargs: str | None):
        stmt = select(cls)
        for k, v in kwargs.items():
            if v is not None:
                stmt = stmt.filter(getattr(cls, k).contains(v))
        return session.get_paginated(stmt, offset, limit)

    @classmethod
    def search_by_username(
        cls,
        session: sessionmaker,
        exclude_id: int,
        search: str | None,
        offset: int,
        limit: int,
    ) -> list[User]:
        stmt = select(cls).filter(cls.id != exclude_id)
        if search is not None:
            stmt = stmt.filter(cls.username.contains(search))
        return session.get_paginated(stmt, offset, limit)

    def get_identity(self):
        return self.id

    def change_email(self, session: sessionmaker, new_email: str) -> bool:
        if User.find_by_email_address(session, new_email):
            return False
        self.email = new_email
        self.email_confirmed = False
        return True

    def change_password(self, new_password: str) -> None:  # auto-commit
        self.password = User.generate_hash(new_password)

    def change_settings(
        self, new_values: dict[str, str | int | bool]
    ) -> None:  # auto-commit
        # TODO redo
        if "username" in new_values:
            self.username = new_values["username"]
        if "dark-theme" in new_values:
            self.dark_theme = new_values["dark-theme"]
        if "language" in new_values:
            self.language = new_values["language"]
        if "name" in new_values:
            self.name = new_values["name"]
        if "surname" in new_values:
            self.surname = new_values["surname"]
        if "patronymic" in new_values:
            self.patronymic = new_values["patronymic"]
        if "bio" in new_values:
            self.bio = new_values["bio"]
        if "group" in new_values:
            self.group = new_values["group"]
        if "avatar" in new_values:
            self.avatar = new_values["avatar"]

    def get_author_status(self) -> str:
        return (
            "not-yet"
            if self.author is None
            else "banned"
            if self.author.banned
            else "current"
        )


UserRole.default_role = User
