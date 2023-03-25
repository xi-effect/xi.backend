from __future__ import annotations

from flask_fullstack import UserRole, PydanticModel, Identifiable
from passlib.hash import pbkdf2_sha256
from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, Float, Date

from ._core import Base, db  # noqa: WPS436


class BlockedToken(Base):
    __tablename__ = "blocked_tokens"

    id = Column(Integer, primary_key=True, unique=True)
    jti = Column(String(36), nullable=False)

    @classmethod
    def find_by_jti(cls, jti: str) -> BlockedToken:
        return db.get_first(select(cls).filter_by(jti=jti))


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
    handle = Column(String(100), nullable=True, unique=True, index=True)

    # profile:
    name = Column(String(100), nullable=True)
    surname = Column(String(100), nullable=True)
    patronymic = Column(String(100), nullable=True)
    birthday = Column(Date, nullable=True)

    # Education data:
    theory_level = Column(Float, nullable=False, default=0.5)
    filter_bind = Column(String(10), nullable=True)

    # Chat-related
    # chats = relationship("UserToChat", back_populates="user")  # TODO remove non-common reference

    # Invite-related
    code = Column(String(100), nullable=True)
    invite_id = Column(
        Integer,
        ForeignKey("invites.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )  # TODO remove non-common reference
    invite = relationship(
        "Invite", back_populates="invited"
    )  # TODO remove non-common reference

    MainData = PydanticModel.column_model(id, username, handle)
    ProfileData = MainData.column_model(
        email, email_confirmed, name, surname, patronymic, birthday, code
    )

    @classmethod
    def find_by_id(cls, entry_id: int) -> User | None:
        return db.get_first(select(cls).filter_by(id=entry_id))

    @classmethod
    def find_by_identity(cls, identity: int) -> User | None:
        return cls.find_by_id(identity)

    @classmethod
    def find_by_handle(cls, handle: str | None, exclude_id: int = None) -> User | None:
        if handle is None:
            return None
        stmt = select(cls).filter_by(handle=handle)
        if exclude_id is not None:
            stmt = stmt.filter(cls.id != exclude_id)
        return db.get_first(stmt)

    @classmethod
    def find_by_email_address(cls, email) -> User | None:
        return db.get_first(select(cls).filter_by(email=email))

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
    def search_by_params(
        cls, offset: int, limit: int, **kwargs: str | None
    ) -> list[User]:
        stmt = select(cls)
        for k, v in kwargs.items():
            if v is not None:
                stmt = stmt.filter(getattr(cls, k).contains(v))
        return db.get_paginated(stmt, offset, limit)

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
        return db.get_paginated(stmt, offset, limit)

    def get_identity(self):
        return self.id

    def change_email(self, new_email: str) -> None:
        self.email = new_email
        self.email_confirmed = False

    def change_password(self, new_password: str) -> None:
        self.password = User.generate_hash(new_password)

    def change_settings(self, **new_values) -> None:
        for key, value in new_values.items():
            if value is not None:
                setattr(self, key, value)


UserRole.default_role = User
