from __future__ import annotations

from datetime import date
from typing import Self

from flask_fullstack import UserRole, Identifiable
from passlib.hash import pbkdf2_sha256
from pydantic_marshals.sqlalchemy import MappedModel
from sqlalchemy import select, ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy.sql.sqltypes import String

from common import Base, db
from common.abstract import SoftDeletable
from communities.base.meta_db import Community, Participant
from users.invites_db import Invite
from vault.files_db import File


class BlockedToken(Base):
    __tablename__ = "blocked_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    jti: Mapped[str] = mapped_column(String(36))

    @classmethod
    def find_by_jti(cls, jti: str) -> BlockedToken:
        return db.get_first(select(cls).filter_by(jti=jti))


class User(SoftDeletable, UserRole, Identifiable):
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
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    email_confirmed: Mapped[bool] = mapped_column(default=False)
    password: Mapped[str] = mapped_column(String(100))

    # Settings:
    username: Mapped[str] = mapped_column(String(100))
    handle: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    theme: Mapped[str] = mapped_column(String(10), default="system")

    # Profile:
    name: Mapped[str | None] = mapped_column(String(100))
    surname: Mapped[str | None] = mapped_column(String(100))
    patronymic: Mapped[str | None] = mapped_column(String(100))
    birthday: Mapped[date | None] = mapped_column()

    # Invite-related
    code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    invite_id: Mapped[int | None] = mapped_column(
        ForeignKey("invites.id", ondelete="SET NULL")
    )
    invite = relationship(Invite, back_populates="invited")

    avatar_id: Mapped[int | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL")
    )
    avatar: Mapped[File | None] = relationship(
        foreign_keys=[avatar_id],
        passive_deletes=True,
    )

    communities_r = relationship("Participant", passive_deletes=True)
    # TODO move to participant

    @property
    def communities(self) -> list[Community]:
        return Participant.get_communities_list(self.id)

    MainData = MappedModel.create(columns=[id, username, handle])
    CommunityModel = MainData.extend(
        relationships=[(avatar, File.FullModel, True)],
        properties=[(communities, list[Community.IndexModel])],
    )

    settings_columns = [email, email_confirmed, theme, code]
    profile_columns = [name, surname, patronymic, birthday]
    ProfileData = MainData.extend(columns=settings_columns + profile_columns)

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_not_deleted(id=entry_id)

    @classmethod
    def find_by_identity(cls, identity: int) -> Self | None:
        return cls.find_by_id(identity)

    @classmethod
    def find_by_handle(cls, handle: str | None, exclude_id: int = None) -> Self | None:
        if handle is None:
            return None
        stmt = select(cls).filter_by(handle=handle)
        if exclude_id is not None:
            stmt = stmt.filter(cls.id != exclude_id)
        return db.get_first(stmt)

    @classmethod
    def find_by_email_address(cls, email) -> Self | None:
        return cls.find_first_by_kwargs(email=email)

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
    ) -> list[Self]:
        stmt = cls.select_not_deleted()
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
    ) -> list[Self]:
        stmt = cls.select_not_deleted().filter(cls.id != exclude_id)
        if search is not None:
            stmt = stmt.filter(cls.username.contains(search))
        return db.get_paginated(stmt, offset, limit)

    def get_identity(self) -> int:
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
