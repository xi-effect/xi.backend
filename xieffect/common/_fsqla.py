from __future__ import annotations

from typing import TypeVar

from flask_fullstack import ModBaseMeta
from flask_sqlalchemy import SQLAlchemy as _SQLAlchemy
from flask_sqlalchemy.model import Model
from sqlalchemy import MetaData, select
from sqlalchemy.engine import Row
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import Select

v = TypeVar("v")
t = TypeVar("t", bound="Model")
m = TypeVar("m", bound="SQLAlchemy.Model")


class CustomModel(Model):
    @classmethod
    def create(cls: type[t], **kwargs) -> t:
        entry = cls(**kwargs)
        cls.__fsa__.session.add(entry)
        cls.__fsa__.session.flush()
        return entry

    @classmethod
    def select_by_kwargs(cls, *order_by, **kwargs) -> Select:
        if len(order_by) == 0:
            return select(cls).filter_by(**kwargs)
        return select(cls).filter_by(**kwargs).order_by(*order_by)

    @classmethod
    def find_first_by_kwargs(cls: type[t], *order_by, **kwargs) -> t | None:
        return cls.__fsa__.get_first(cls.select_by_kwargs(*order_by, **kwargs))

    @classmethod
    def find_all_by_kwargs(cls: type[t], *order_by, **kwargs) -> list[t]:
        return cls.__fsa__.get_all(cls.select_by_kwargs(*order_by, **kwargs))

    @classmethod
    def find_paginated_by_kwargs(
        cls: type[t], offset: int, limit: int, *order_by, **kwargs
    ) -> list[t]:
        return cls.__fsa__.get_paginated(
            cls.select_by_kwargs(*order_by, **kwargs), offset, limit
        )

    def delete(self) -> None:
        self.__fsa__.session.delete(self)
        self.__fsa__.session.flush()


# TODO proper type annotations for Select (mb python3.11's Self type)
# noinspection PyUnresolvedReferences
class SQLAlchemy(_SQLAlchemy):
    DEFAULT_ENGINE_OPTIONS = {"pool_recycle": 280}
    DEFAULT_CONVENTION = {
        "ix": "ix_%(column_0_label)s",  # noqa: WPS323
        "uq": "uq_%(table_name)s_%(column_0_name)s",  # noqa: WPS323
        "ck": "ck_%(table_name)s_%(constraint_name)s",  # noqa: WPS323
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # noqa: WPS323
        "pk": "pk_%(table_name)s",  # noqa: WPS323
    }

    def __init__(
        self,
        app: Flask,
        db_url: str,
        naming_convention: dict | None = None,
        echo: bool = False,
        **kwargs,
    ) -> None:
        app.config["SQLALCHEMY_DATABASE_URI"] = db_url
        super().__init__(
            app=app,
            metadata=kwargs.get(
                "metadata",
                MetaData(
                    naming_convention=naming_convention or self.DEFAULT_CONVENTION
                ),
            ),
            engine_options=dict(
                kwargs.get("engine_options", self.DEFAULT_ENGINE_OPTIONS), echo=echo
            ),
            model_class=kwargs.get(
                "model_class",
                declarative_base(cls=CustomModel, metaclass=ModBaseMeta),
            ),
            **kwargs,
        )

    def with_autocommit(self, result: v = None) -> v:
        self.session.commit()
        return result

    def get_first(self, stmt: Select) -> m | None:
        return self.session.execute(stmt).scalars().first()

    def get_first_row(self, stmt: Select) -> Row:
        return self.session.execute(stmt).first()

    def get_all(self, stmt: Select) -> list[m]:
        return self.session.execute(stmt).scalars().all()

    def get_all_rows(self, stmt: Select) -> list[Row]:
        return self.session.execute(stmt).all()

    def get_paginated(self, stmt: Select, offset: int, limit: int) -> list[m]:
        return self.get_all(stmt.offset(offset).limit(limit))

    def get_paginated_rows(self, stmt: Select, offset: int, limit: int) -> list[Row]:
        return self.get_all_rows(stmt.offset(offset).limit(limit))
