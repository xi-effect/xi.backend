from __future__ import annotations

from functools import wraps
from typing import Type, Optional, Any, List

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace as RestXNamespace
from flask_restx.reqparse import RequestParser
from sqlalchemy.engine import Result

from main import Session, Base, index_service
from .add_whoosh import Searcher
from .marshals import ResponseDoc, success_response, message_response


class Identifiable:
    """
    An interface to mark database classes that have an id and can be identified by it.

    Used in :ref:`.Namespace.database_searcher`
    """

    not_found_text: str = ""
    """ Customizable error message to be used for missing ids """

    def __init__(self, **kwargs):
        pass

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> Optional[Identifiable]:
        raise NotImplementedError


class UserRole(Identifiable):
    """
    An interface to mark database classes as user roles, that can be used for authorization.

    Used in :ref:`.Namespace.jwt_authorizer`
    """

    default_role = None

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> Optional[UserRole]:
        raise NotImplementedError


def get_or_pop(dictionary: dict, key, keep: bool = False):
    return dictionary[key] if keep else dictionary.pop(key)


def first_or_none(result: Result) -> Optional[Any]:
    """ Wrapper for database result object (gets the first one or None) """
    if (first := result.first()) is None:
        return None
    return first[0]


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


class Namespace(RestXNamespace):
    """
    Expansion of :class:`RestXNamespace`, which adds decorators for methods of :class:`Resource`.

    Methods of this class (used as decorators) allow parsing request parameters,
    modifying responses and automatic updating Swagger documentation where possible
    """

    auth_errors: List[ResponseDoc] = [
        ResponseDoc(401, "JWTError", message_response.model),
        ResponseDoc(422, "InvalidJWT", message_response.model)
    ]

    def doc_responses(self, *responses: ResponseDoc):
        """
        Adds responses to the documentation. **Affects docs only!**

        :param responses: all responses to document. Models inside are registered automatically.
        """

        def doc_responses_wrapper(function):
            for response in responses:
                response.register_model(self)
                function = self.response(*response.get_args())(function)
            return function

        return doc_responses_wrapper

    def a_response(self):
        """
        - Wraps Resource's method return with ``{"a": <something>}`` response and updates documentation.
        - Defines response type automatically by looking at method's return type annotation.
        """

        def a_response_wrapper(function):
            return_type: Type = getattr(function, "__annotations__")["return"]
            is_bool = return_type is None or issubclass(return_type, bool)

            @self.response(*(success_response if is_bool else message_response).get_args())
            @wraps(function)
            def a_response_inner(*args, **kwargs):
                result = function(*args, **kwargs)
                return {"a": True if return_type is None else result}

            return a_response_inner

        return a_response_wrapper

    @staticmethod
    def _database_searcher(identifiable: Type[Identifiable], input_field_name: str,
                           result_filed_name: Optional[str], check_only: bool,
                           use_session: bool, error_code: int, callback, *args, **kwargs):
        session = get_or_pop(kwargs, "session", use_session)
        target_id: int = get_or_pop(kwargs, input_field_name, check_only)
        if (result := identifiable.find_by_id(session, target_id)) is None:
            return {"a": identifiable.not_found_text}, error_code
        else:
            if not check_only and result_filed_name is not None:
                kwargs[result_filed_name] = result
            return callback(*args, **kwargs)

    def jwt_authorizer(self, role: Type[UserRole], check_only: bool = False, use_session: bool = True):
        """
        - Authorizes user by JWT-token.
        - If token is missing or is not processable, falls back on flask-jwt-extended error handlers.
        - If user doesn't exist or doesn't have the role required, sends the corresponding response.
        - All error responses are added to the documentation automatically.
        - Can pass user and session objects to the decorated function.

        :param role: role to expect
        :param check_only: (default: False) if True, user object won't be passed to the decorated function
        :param use_session: (default: True) whether or not to pass the session to the decorated function
        """

        def authorizer_wrapper(function):
            error_code: int = 401 if role is UserRole.default_role else 403

            @self.doc_responses(*self.auth_errors, ResponseDoc.error_response(error_code, role.not_found_text))
            @self.doc(security="jwt")
            @wraps(function)
            @jwt_required()
            @with_session
            def authorizer_inner(*args, **kwargs):
                kwargs["id"] = get_jwt_identity()
                return self._database_searcher(role, "id", None if check_only else role.__name__.lower(), False,
                                               use_session, error_code, function, *args, **kwargs)

            return authorizer_inner

        return authorizer_wrapper

    def database_searcher(self, identifiable: Type[Identifiable], input_field_name: str,
                          result_filed_name: Optional[str] = None, check_only: bool = False, use_session: bool = False):
        """
        - Uses incoming id argument to find something :class:`Identifiable` in the database.
        - If the entity wasn't found, will return a 404 response, which is documented automatically.
        - Can pass (entity's id or entity) and session objects to the decorated function.

        :param identifiable: identifiable to search for
        :param input_field_name: field name were the entity's id is held. This field will be gone if not check_only
        :param result_filed_name: the name of field to pass the entity to. If None, doesn't pass anything
        :param check_only: (default: False) if True, checks if entity exists and passes id to the decorated function
        :param use_session: (default: False) whether or not to pass the session to the decorated function
        """

        def searcher_wrapper(function):
            @self.response(*ResponseDoc.error_response(404, identifiable.not_found_text).get_args())
            @wraps(function)
            @with_session
            def searcher_inner(*args, **kwargs):
                return self._database_searcher(identifiable, input_field_name, result_filed_name, check_only,
                                               use_session, 404, function, *args, **kwargs)

            return searcher_inner

        return searcher_wrapper

    def argument_parser(self, parser: RequestParser):
        """
        - Parses request parameters and adds them to kwargs used to call the decorated function.
        - Automatically updates endpoint's parameters with arguments from the parser.
        """

        def argument_wrapper(function):
            @self.expect(parser)
            @wraps(function)
            def argument_inner(*args, **kwargs):
                kwargs.update(parser.parse_args())
                return function(*args, **kwargs)

            return argument_inner

        return argument_wrapper

    def lister(self, per_request: int, marshal_model, skip_none: bool = True, **kwargs):
        """
        - Used for organising pagination.
        - Uses `counter` form incoming arguments for the decorated function and `per_request` argument
          to define start and finish indexes, passed as keyword arguments to the decorated function.
        - Marshals the return of the decorated function as a list with `marshal_model`.
        - Adds information on the response to documentation automatically.

        :raises KeyError: if counter argument is not provided
        :param per_request:
        :param marshal_model:
        :param skip_none:
        :param kwargs:
        :return:
        """

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
