from functools import wraps
from typing import Type, Optional, Union, Callable, Any

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace as RestXNamespace
from flask_restx.reqparse import RequestParser
from sqlalchemy.engine import Result

from main import Session, Base, index_service
from .add_whoosh import Searcher
from .marshals import ResponseDoc, success_response, message_response


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
    @wraps(function)
    def with_session_inner(*args, **kwargs):
        with Session.begin() as session:
            kwargs["session"] = session
            return function(*args, **kwargs)

    return with_session_inner


def with_auto_session(function):
    @wraps(function)
    def with_auto_session_inner(*args, **kwargs):
        with Session.begin() as _:
            return function(*args, **kwargs)

    return with_auto_session_inner


class Namespace(RestXNamespace):
    def doc_responses(self, *responses: ResponseDoc):
        def doc_responses_wrapper(function):
            for response in responses:
                response.register_model(self)  # do?
                function = self.response(*response.get_args())(function)
            return function

        return doc_responses_wrapper

    def a_response(self):
        def bool_a_response_wrapper(function: Callable[[Any], Union[None, bool, str]]):
            return_type: Type = getattr(function, "__annotations__")["return"]
            is_bool = return_type is None or issubclass(return_type, bool)

            @wraps(function)
            def bool_a_response_inner(*args, **kwargs):
                result = function(*args, **kwargs)
                return {"a": True if return_type is None else result}

            return self.response(*(success_response if is_bool else message_response).get_args())(bool_a_response_inner)

        return bool_a_response_wrapper

    def jwt_authorizer(self, role: Type[UserRole], chek_only: bool = False, use_session: bool = True):
        def authorizer_wrapper(function):
            response_code: int = 401 if role is UserRole.default_role else 403

            @wraps(function)
            @jwt_required()
            @with_session
            def authorizer_inner(*args, **kwargs):
                session = kwargs["session"]
                result: role = role.find_by_id(session, get_jwt_identity())
                if result is None:
                    return {"a": role.not_found_text}, response_code
                else:
                    if not chek_only:
                        kwargs[role.__name__.lower()] = result
                    if not use_session:
                        kwargs.pop("session")
                    return function(*args, **kwargs)

            return self.response(
                *ResponseDoc.error_response(response_code, role.not_found_text).get_args())(authorizer_inner)

        return authorizer_wrapper

    def database_searcher(self, identifiable: Type[Identifiable], input_field_name: str,
                          result_filed_name: Optional[str] = None, check_only: bool = False, use_session: bool = False):
        def searcher_wrapper(function):
            error_response: tuple = {"a": identifiable.not_found_text}, 404

            @wraps(function)
            @with_session
            def searcher_inner(*args, **kwargs):
                session = kwargs["session"] if use_session else kwargs.pop("session")
                target_id: int = kwargs.pop(input_field_name)
                result: identifiable = identifiable.find_by_id(session, target_id)
                if result is None:
                    return error_response
                else:
                    if result_filed_name is not None:
                        kwargs[result_filed_name] = result
                    return function(*args, **kwargs)

            @wraps(function)
            @with_session
            def checker_inner(*args, **kwargs):
                session = kwargs["session"] if use_session else kwargs.pop("session")
                if identifiable.find_by_id(session, kwargs[input_field_name]) is None:
                    return error_response
                else:
                    return function(*args, **kwargs)

            result = checker_inner if check_only else searcher_inner
            return self.response(*ResponseDoc.error_response(404, identifiable.not_found_text).get_args())(result)

        return searcher_wrapper

    def argument_parser(self, parser: RequestParser):
        def argument_wrapper(function):
            @wraps(function)
            def argument_inner(*args, **kwargs):
                kwargs.update(parser.parse_args())
                return function(*args, **kwargs)

            return self.expect(parser)(argument_inner)

        return argument_wrapper

    def lister(self, per_request: int, marshal_model, skip_none: bool = True, **kwargs):
        def lister_wrapper(function):
            @wraps(function)
            @self.marshal_list_with(marshal_model, skip_none=skip_none, **kwargs)
            def lister_inner(*args, **kwargs):
                counter: int = kwargs.pop("counter") * per_request
                kwargs["start"] = counter
                kwargs["finish"] = counter + per_request
                return function(*args, **kwargs)

            return lister_inner

        return lister_wrapper


"""
def yad(decorators):
    def decorator(f):
        __apidoc__ = f.__apidoc__
        for d in reversed(decorators):
            f = d(f)
        f.__apidoc__ = __apidoc__
        return f

    return decorator


def cool_marshal_with(model: Dict[str, Type[Raw]], namespace: Namespace, *decorators, as_list: bool = False):
    def cool_marshal_with_wrapper(function):
        @yad(decorators)
        @namespace.marshal_with(model, skip_none=True, as_list=as_list)
        def cool_marshal_with_inner(*args, **kwargs):
            return function(*args, **kwargs)

        return cool_marshal_with_inner

    return cool_marshal_with_wrapper
"""
