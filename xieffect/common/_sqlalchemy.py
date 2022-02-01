from __future__ import annotations

from functools import wraps
from typing import Type

from main import Session, Base, index_service
from sqlalchemy import JSON
from ._whoosh import Searcher


def register_as_searchable(*searchable: str):
    """
    - Registers database model as searchable with whoosh-sqlalchemy.
    - Adds ``search_stmt`` field (:class:`Searcher`) to the class for searching.

    :param searchable: names of model's fields to create the whoosh schema on
    """

    def register_as_searchable_wrapper(model: Type[Base]):
        model.__searchable__ = list(searchable)
        index_service.register_class(model)

        searcher = model.search_query
        model.search_stmt = Searcher(searcher.model_class, searcher.primary, searcher.index)

        return model

    return register_as_searchable_wrapper


def with_session(function):
    """ Wraps the function with Session.begin() and passes session object to the decorated function """

    @wraps(function)
    def with_session_inner(*args, **kwargs):
        if "session" in kwargs.keys():
            return function(*args, **kwargs)
        with Session.begin() as session:
            kwargs["session"] = session
            return function(*args, **kwargs)

    return with_session_inner


def with_auto_session(function):
    """ Wraps the function with Session.begin() for automatic commits after the decorated function """

    @wraps(function)
    def with_auto_session_inner(*args, **kwargs):
        with Session.begin() as _:
            return function(*args, **kwargs)

    return with_auto_session_inner


class JSONWithModel(JSON):
    def __init__(self, model_name: str, model: dict, as_list: bool = False, none_as_null=False):
        super().__init__(none_as_null)
        self.model_name: str = model_name
        self.model: dict = model
        self.as_list: bool = as_list


class JSONWithSchema(JSON):
    def __init__(self, schema_type: str, schema_format=None, schema_example=None, none_as_null=False):
        super().__init__(none_as_null)
        self.schema_type = schema_type
        self.schema_format = schema_format
        self.schema_example = schema_example
