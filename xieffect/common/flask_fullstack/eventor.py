from typing import Union, Type

from .interfaces import Identifiable
from .sqlalchemy import Sessionmaker
from .utils import get_or_pop
from ..flask_siox import EventGroup as _EventGroup


class EventGroup(_EventGroup):  # TODO externalize to flask-fullstack
    def __init__(self, sessionmaker: Sessionmaker, use_kebab_case: bool = False):
        super().__init__(use_kebab_case)
        self.with_begin = sessionmaker.with_begin

    def abort(self, error_code: Union[int, str], description: str):
        raise NotImplementedError

    def _database_searcher(self, identifiable: Type[Identifiable], check_only: bool, no_id: bool,
                           use_session: bool, error_code: int, callback, args, kwargs, *,
                           input_field_name: Union[str, None] = None, result_field_name: Union[str, None] = None):
        if input_field_name is None:
            input_field_name = identifiable.__name__.lower() + "_id"
        if result_field_name is None:
            result_field_name = identifiable.__name__.lower()
        session = get_or_pop(kwargs, "session", use_session)
        target_id: int = get_or_pop(kwargs, input_field_name, check_only and not no_id)
        if (result := identifiable.find_by_id(session, target_id)) is None:
            self.abort(error_code, identifiable.not_found_text)
        else:
            if not check_only:
                kwargs[result_field_name] = result
            return callback(*args, **kwargs)
