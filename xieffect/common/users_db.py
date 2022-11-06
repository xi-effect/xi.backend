from __future__ import annotations

from collections.abc import Callable

from flask_fullstack import UserRole, PydanticModel, Identifiable
from passlib.hash import pbkdf2_sha256
from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, Float, Text, JSON

from ._core import Base, db  # noqa: WPS436

DEFAULT_AVATAR: dict = {  # noqa: WPS407
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
    def find_by_jti(cls, jti: str) -> BlockedToken:
        return db.session.get_first(select(cls).filter_by(jti=jti))


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

    CHANGEABLE_FIELDS = tuple(
        (field, field.replace("_", "-"))
        for field in (
            "username",
            "dark_theme",
            "language",
            "name",
            "surname",
            "patronymic",
            "bio",
            "group",
            "avatar",
        )
    )

    class RoleSettings(PydanticModel):  # TODO pragma: no coverage
        author_status: str
        moderator_status: bool

        @classmethod
        def callback_convert(cls, callback: Callable, orm_object: User, **_) -> None:
            callback(
                author_status=orm_object.author_status(),
                moderator_status=orm_object.moderator is not None,
            )

    @classmethod
    def find_by_id(cls, entry_id: int) -> User | None:
        return db.session.get_first(select(cls).filter_by(id=entry_id))

    @classmethod
    def find_by_identity(cls, identity: int) -> User | None:
        return cls.find_by_id(identity)

    @classmethod
    def find_by_email_address(cls, email) -> User | None:
        return db.session.get_first(select(cls).filter_by(email=email))

    @classmethod  # TODO this class shouldn't know about invites
    def create(
        cls,
        *,
        email: str,
        password: str,
        invite=None,
        **kwargs,
    ) -> User | None:
        if cls.find_by_email_address(email):
            return None
        new_user = super().create(
            email=email,
            password=cls.generate_hash(password),
            invite=invite,
            **kwargs,
        )
        if invite is not None:
            new_user.code = new_user.invite.generate_code(new_user.id)
            db.session.flush()
        return new_user

    @classmethod
    def search_by_params(cls, offset: int, limit: int, **kwargs: str | None):
        stmt = select(cls)
        for k, v in kwargs.items():
            if v is not None:
                stmt = stmt.filter(getattr(cls, k).contains(v))
        return db.session.get_paginated(stmt, offset, limit)

    @classmethod
    def search_by_username(
        cls,
        exclude_id: int,
        search: str | None,
        offset: int,
        limit: int,
    ) -> list[User]:
        stmt = select(cls).filter(cls.id != exclude_id)
        if search is not None:
            stmt = stmt.filter(cls.username.contains(search))
        return db.session.get_paginated(stmt, offset, limit)

    def get_identity(self):
        return self.id

    def change_email(self, new_email: str) -> bool:  # TODO pragma: no coverage
        if User.find_by_email_address(new_email):
            return False
        self.email = new_email
        self.email_confirmed = False
        return True

    def change_password(self, new_password: str) -> None:  # TODO pragma: no coverage
        self.password = User.generate_hash(new_password)

    def change_settings(self, new_values: dict[str, str | int | bool]) -> None:
        for attribute, field in self.CHANGEABLE_FIELDS:
            value = new_values.get(field)
            if value is not None:
                setattr(self, attribute, value)

    def author_status(self) -> str:  # TODO pragma: no coverage (with RoleModel)
        if self.author is None:
            return "not-yet"
        return "banned" if self.author.banned else "current"


UserRole.default_role = User
