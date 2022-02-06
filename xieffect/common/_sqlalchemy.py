from __future__ import annotations

from functools import wraps

from sqlalchemy import JSON
from sqlalchemy.orm import sessionmaker


class Sessionmaker(sessionmaker):
    def with_begin(self, function):
        """ Wraps the function with Session.begin() and passes session object to the decorated function """

        @wraps(function)
        def with_begin_inner(*args, **kwargs):
            if "session" in kwargs.keys():
                return function(*args, **kwargs)
            with self.begin() as session:
                kwargs["session"] = session
                return function(*args, **kwargs)

        return with_begin_inner

    def with_autocommit(self, function):
        """ Wraps the function with Session.begin() for automatic commits after the decorated function """

        @wraps(function)
        def with_autocommit_inner(*args, **kwargs):
            with self.begin() as _:
                return function(*args, **kwargs)

        return with_autocommit_inner


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
