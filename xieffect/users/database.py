from typing import Dict, Union

from passlib.hash import pbkdf2_sha256 as sha256
from sqlalchemy import Column
from sqlalchemy.sql.sqltypes import Integer, String, Boolean

from authorship import Moderator, Author
from componets import UserRole
from main import Base, Session


class TokenBlockList(Base):
    id = Column(Integer, primary_key=True, unique=True)
    jti = Column(String(36), nullable=False)

    @classmethod
    def find_by_jti(cls, session: Session, jti):
        return cls.query(TokenBlockList.id).filter_by(jti=jti).scalar()

    @classmethod
    def add_by_jti(cls, session: Session, jti):
        session.add(TokenBlockList(jti=jti))
        session.commit()


class User(Base, UserRole):
    __tablename__ = "users"
    not_found_text = "User does not exist"

    @staticmethod
    def generate_hash(password):
        return sha256.hash(password)

    @staticmethod
    def verify_hash(password, hashed):
        return sha256.verify(password, hashed)

    # Vital:
    id = Column(Integer, primary_key=True)
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

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    @classmethod
    def find_by_email_address(cls, session: Session, email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def create(cls, session: Session, email: str, username: str, password: str):
        if cls.find_by_email_address(session, email):
            return None
        new_user = cls(email=email, password=cls.generate_hash(password), username=username)
        session.add(new_user)
        session.commit()
        return new_user

    def confirm_email(self):  # auto-commit
        self.email_confirmed = True

    def change_email(self, session: Session, new_email: str) -> bool:
        if User.find_by_email_address(session, new_email):
            return False
        self.email = new_email
        self.email_confirmed = False
        session.commit()
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

    def get_role_settings(self, session: Session) -> Dict[str, str]:
        return {
            "moderator": Moderator.find_by_id(session, self.id) is not None,
            "author": "not-yet" if (author := Author.find_by_id(session, self.id, include_banned=True)
                                    ) is None else "banned" if author.banned else "current"
        }

    def get_main_settings(self) -> Dict[str, str]:
        return {"username": self.username, "dark-theme": self.dark_theme, "language": self.language}

    def get_settings(self) -> Dict[str, str]:
        return {
            "email": self.email, "email-confirmed": self.email_confirmed, "username": self.username,
            "name": self.name, "surname": self.surname, "patronymic": self.patronymic,
            "dark-theme": self.dark_theme, "language": self.language
        }

    def get_filter_bind(self) -> str:
        return self.filter_bind

    def set_filter_bind(self, bind: str = None) -> None:  # auto-commit
        self.filter_bind = bind


UserRole.default_role = User
