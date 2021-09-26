from typing import Type, Optional, Union, Tuple, Callable, Any

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful.reqparse import RequestParser
from sqlalchemy.engine import Result

from componets.add_whoosh import Searcher
from componets.parsers import counter_parser
from main import Session, Base, index_service


class Identifiable:
    not_found_text: str = ""

    def __init__(self, **kwargs):
        pass

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int):
        raise NotImplementedError


class UserRole:
    not_found_text: str = ""
    default_role = None

    def __init__(self, **kwargs):
        pass

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int):
        raise NotImplementedError


def first_or_none(result: Result):
    if (first := result.first()) is None:
        return None
    return first[0]


def register_as_searchable(*searchable: str):
    def register_as_searchable_wrapper(model: Type[Base]):
        model.__searchable__ = list(searchable)
        index_service.register_class(model)

        searcher = model.search_query
        model.search_stmt = Searcher(searcher.model_class, searcher.primary, searcher.index)

        return model

    return register_as_searchable_wrapper


def with_session(function):
    def with_session_inner(*args, **kwargs):
        with Session.begin() as session:
            kwargs["session"] = session
            return function(*args, **kwargs)

    return with_session_inner


def with_auto_session(function):
    def with_auto_session_inner(*args, **kwargs):
        with Session.begin() as _:
            return function(*args, **kwargs)

    return with_auto_session_inner


def jwt_authorizer(role: Type[UserRole], result_filed_name: Optional[str] = "user", use_session: bool = True):
    def authorizer_wrapper(function):
        @jwt_required()
        @with_session
        def authorizer_inner(*args, **kwargs):
            session = kwargs["session"]
            result: role = role.find_by_id(session, get_jwt_identity())
            if result is None:
                return {"a": role.not_found_text}, 401 if role is UserRole.default_role else 403
            else:
                if result_filed_name is not None:
                    kwargs[result_filed_name] = result
                if not use_session:
                    kwargs.pop("session")
                return function(*args, **kwargs)

        return authorizer_inner

    return authorizer_wrapper


def database_searcher(identifiable: Type[Identifiable], input_field_name: str,
                      result_filed_name: Optional[str] = None, check_only: bool = False):
    def searcher_wrapper(function):
        error_response: tuple = {"a": identifiable.not_found_text}, 404

        @with_session
        def searcher_inner(*args, **kwargs):
            session = kwargs.pop("session")
            target_id: int = kwargs.pop(input_field_name)
            result: identifiable = identifiable.find_by_id(session, target_id)
            if result is None:
                return error_response
            else:
                if result_filed_name is not None:
                    kwargs[result_filed_name] = result
                return function(*args, **kwargs)

        @with_session
        def checker_inner(session, *args, **kwargs):
            if identifiable.find_by_id(session, kwargs[input_field_name]) is None:
                return error_response
            else:
                return function(*args, **kwargs)

        if check_only:
            return checker_inner
        else:
            return searcher_inner

    return searcher_wrapper


def argument_parser(parser: RequestParser, *arg_names: Union[str, Tuple[str, str]]):
    def argument_wrapper(function):
        def argument_inner(*args, **kwargs):
            data: dict = parser.parse_args()
            for arg_name in arg_names:
                if isinstance(arg_name, str):
                    kwargs[arg_name] = data[arg_name]
                else:
                    kwargs[arg_name[1]] = data[arg_name[0]]
            return function(*args, **kwargs)

        return argument_inner

    return argument_wrapper


def lister(per_request: int, argument_parser: Callable[[Callable], Any] = argument_parser(counter_parser, "counter")):
    def lister_wrapper(function):
        @argument_parser
        def lister_inner(*args, **kwargs):
            counter: int = kwargs.pop("counter") * per_request
            kwargs["start"] = counter
            kwargs["finish"] = counter + per_request
            return function(*args, **kwargs)

        return lister_inner

    return lister_wrapper
