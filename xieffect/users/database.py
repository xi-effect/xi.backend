from typing import Dict, Union

from passlib.hash import pbkdf2_sha256 as sha256
from sqlalchemy import Column, Sequence, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Boolean

from componets import UserRole, create_marshal_model, Marshalable, LambdaFieldDef
from componets.checkers import first_or_none
from main import Base, Session


class TokenBlockList(Base):
    __tablename__ = "token_block_list"

    id = Column(Integer, Sequence('tbl_id_seq'), primary_key=True, unique=True)
    jti = Column(String(36), nullable=False)

    @classmethod
    def find_by_jti(cls, session: Session, jti):
        return first_or_none(session.execute(select(cls).where(cls.jti == jti)))

    @classmethod
    def add_by_jti(cls, session: Session, jti):
        session.add(cls(jti=jti))


@create_marshal_model("main-settings", "username", "dark_theme", "language")
@create_marshal_model("full-settings", "filter_bind", "password", "id", full=True)
@create_marshal_model("role-settings")
class User(Base, UserRole, Marshalable):
    __tablename__ = "users"
    not_found_text = "User does not exist"

    @staticmethod
    def generate_hash(password):
        return sha256.hash(password)

    @staticmethod
    def verify_hash(password, hashed):
        return sha256.verify(password, hashed)

    # Vital:
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    email = Column(String(100), nullable=False, unique=True)
    email_confirmed = Column(Boolean, nullable=False, default=False)
    password = Column(String(100), nullable=False)

    # Settings:
    username = Column(String(100), nullable=False)
    dark_theme = Column(Boolean, nullable=False, default=True)
    language = Column(String(20), nullable=False, default="russian")

    # Real name:
    name = Column(String(100), nullable=True)
    surname = Column(String(100), nullable=True)
    patronymic = Column(String(100), nullable=True)

    # Education data:
    filter_bind = Column(String(10), nullable=True)

    # Role-related:  # need to redo user_roles with relations
    author = relationship("Author", backref="user", uselist=False)
    moderator = relationship("Moderator", backref="user", uselist=False)

    author_status: LambdaFieldDef = LambdaFieldDef("role-settings", str, lambda user: user.get_author_status())
    moderator_status: LambdaFieldDef = LambdaFieldDef("role-settings", bool, lambda user: user.moderator is not None)

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int):
        return first_or_none(session.execute(select(cls).where(cls.id == entry_id)))

    @classmethod
    def find_by_email_address(cls, session: Session, email):
        # send_generated_email(email, "pass", "password-reset-email.html")
        return first_or_none(session.execute(select(cls).where(cls.email == email)))

    @classmethod
    def create(cls, session: Session, email: str, username: str, password: str):
        if cls.find_by_email_address(session, email):
            return None
        new_user = cls(email=email, password=cls.generate_hash(password), username=username)
        session.add(new_user)
        return new_user

    def confirm_email(self):  # auto-commit
        self.email_confirmed = True

    def change_email(self, session: Session, new_email: str) -> bool:
        if User.find_by_email_address(session, new_email):
            return False
        self.email = new_email
        self.email_confirmed = False
        return True

    def change_password(self, new_password: str):  # auto-commit
        self.password = User.generate_hash(new_password)

    def change_settings(self, new_values: Dict[str, Union[str, int, bool]]):  # auto-commit
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

    def get_author_status(self):
        return "not-yet" if self.author is None else "banned" if self.author.banned else "current"

    def get_filter_bind(self) -> str:
        return self.filter_bind

    def set_filter_bind(self, bind: str = None) -> None:  # auto-commit
        self.filter_bind = bind


UserRole.default_role = User
