from __future__ import annotations

from json import dumps
from typing import Dict, Union, Optional

from itsdangerous.url_safe import URLSafeSerializer
from passlib.hash import pbkdf2_sha256 as sha256
from sqlalchemy import Column, Sequence, select, ForeignKey
from sqlalchemy.engine import Row
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, Float, Text, JSON
from sqlalchemy_enum34 import EnumType

from componets import UserRole, create_marshal_model, Marshalable, LambdaFieldDef, TypeEnum
from componets.checkers import first_or_none
from main import Base, Session, app

DEFAULT_AVATAR: str = '{"accessory": 0, "body": 0, "face": 0, "hair": 0, "facialHair": 0, "bgcolor": 0}'


class TokenBlockList(Base):
    __tablename__ = "token_block_list"

    id = Column(Integer, Sequence('tbl_id_seq'), primary_key=True, unique=True)
    jti = Column(String(36), nullable=False)

    @classmethod
    def find_by_jti(cls, session: Session, jti) -> TokenBlockList:
        return first_or_none(session.execute(select(cls).where(cls.jti == jti)))

    @classmethod
    def add_by_jti(cls, session: Session, jti) -> None:
        session.add(cls(jti=jti))


@create_marshal_model("user-index", "username", "id", "bio", "avatar")
@create_marshal_model("profile", "name", "surname", "patronymic", "username",
                      "bio", "group", "avatar")
@create_marshal_model("full-settings", "email", "email_confirmed", "avatar",
                      "name", "surname", "patronymic", "bio", "group", inherit="main-settings")
@create_marshal_model("main-settings", "id", "username", "dark_theme", "language")
@create_marshal_model("role-settings")
class User(Base, UserRole, Marshalable):
    __tablename__ = "users"
    not_found_text = "User does not exist"

    @staticmethod
    def generate_hash(password) -> str:
        return sha256.hash(password)

    @staticmethod
    def verify_hash(password, hashed) -> bool:
        return sha256.verify(password, hashed)

    # Vital:
    id = Column(Integer, Sequence("user_id_seq"), primary_key=True)
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

    # Role-related:  # need to redo user_roles with relations
    author = relationship("Author", backref="user", uselist=False)
    moderator = relationship("Moderator", backref="user", uselist=False)

    author_status: LambdaFieldDef = LambdaFieldDef("role-settings", str, lambda user: user.get_author_status())
    moderator_status: LambdaFieldDef = LambdaFieldDef("role-settings", bool, lambda user: user.moderator is not None)

    # Chat-related
    chats = relationship("UserToChat", back_populates="user")

    # invites code-related
    invite_id = Column(Integer, ForeignKey("invites.id"), nullable=True)

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> Optional[User]:
        return first_or_none(session.execute(select(cls).where(cls.id == entry_id)))

    @classmethod
    def find_by_email_address(cls, session: Session, email) -> Optional[User]:
        # send_generated_email(email, "pass", "password-reset-email.html")
        return first_or_none(session.execute(select(cls).where(cls.email == email)))

    @classmethod
    def create(cls, session: Session, email: str, username: str, password: str, invite: Invite = None) -> Optional[User]:
        if cls.find_by_email_address(session, email):
            return None
        new_user = cls(email=email, password=cls.generate_hash(password), username=username)
        if invite is not None:
            new_user.invite_id = invite.id
        session.add(new_user)
        return new_user

    @classmethod
    def search_by_username(cls, session: Session, exclude_id: int, search: Optional[str],
                           offset: int, limit: int) -> list[User]:
        stmt = select(cls).filter(cls.id != exclude_id)
        if search is not None:
            stmt = stmt.filter(cls.username.contains(search))
        return session.execute(stmt.offset(offset).limit(limit)).scalars().all()

    def confirm_email(self) -> None:  # auto-commit
        self.email_confirmed = True

    def change_email(self, session: Session, new_email: str) -> bool:
        if User.find_by_email_address(session, new_email):
            return False
        self.email = new_email
        self.email_confirmed = False
        return True

    def change_password(self, new_password: str) -> None:  # auto-commit
        self.password = User.generate_hash(new_password)

    def change_settings(self, new_values: Dict[str, Union[str, int, bool]]) -> None:  # auto-commit
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
            self.avatar = dumps(new_values["avatar"])

    def get_author_status(self) -> str:
        return "not-yet" if self.author is None else "banned" if self.author.banned else "current"

    def get_filter_bind(self) -> str:
        return self.filter_bind

    def set_filter_bind(self, bind: str = None) -> None:  # auto-commit
        self.filter_bind = bind


UserRole.default_role = User


@create_marshal_model("invite", "name", "code", "limit", "accepted")
class Invite(Base, UserRole, Marshalable):
    # invites
    __tablename__ = "invites"
    serializer: URLSafeSerializer = URLSafeSerializer(app.config["SECRET_KEY"])

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=True)
    code = Column(String, default="")
    limit = Column(Integer, nullable=True)
    accepted = Column(Integer, nullable=False, default=0)
    
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    creator = relationship("User", foreign_keys=[creator_id])
    invited = relationship("User", foreign_keys=[User.invite_id])

    @classmethod
    def create(cls, session: Session, name: str = None, limit: int = None, creator: User = None) -> Invite:
        entry: cls = cls(name=name, limit=limit, creator=creator)
        session.add(entry)
        session.flush()
        entry.code = cls.serializer.dumps(entry.id)
        return entry

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> Optional[Invite]:
        return first_or_none(session.execute(select(cls).filter(cls.id == entry_id)))

    @classmethod
    def find_global(cls, session: Session, offset: int, limit: int) -> list[Invite]:
        stmt = select(cls).filter(cls.creator_id.is_(None))
        return session.execute(stmt.offset(offset).limit(limit)).scalars().all()


class FeedbackType(TypeEnum):
    GENERAL = 0
    BUG_REPORT = 1
    CONTENT_REPORT = 2


@create_marshal_model("feedback-full", "id", "user-id", "type", "data")
class Feedback(Base, Marshalable):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    type = Column(EnumType(FeedbackType, by_name=True), nullable=False)
    data = Column(JSON, nullable=False)

    @classmethod
    def create(cls, session: Session, user: User, feedback_type: FeedbackType, data) -> Feedback:
        new_user = cls(user_id=user.id, type=feedback_type, data=dumps(data, ensure_ascii=False))
        session.add(new_user)
        return new_user

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> list[Feedback]:
        return session.execute(select(cls).where(cls.id == entry_id)).scalars().first()

    @classmethod
    def dump_all(cls, session: Session) -> list[Row]:
        stmt = select(*cls.__table__.columns, *User.__table__.columns).outerjoin(User, User.id == cls.user_id)
        return session.execute(stmt).all()


class FeedbackImage(Base):
    __tablename__ = "feedback-images"

    id = Column(Integer, primary_key=True)

    @classmethod
    def create(cls, session: Session) -> FeedbackImage:
        session.add(new_user := cls())
        return new_user
