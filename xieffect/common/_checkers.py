from __future__ import annotations

from functools import wraps
from typing import Union, Type

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace as RestXNamespace, Model, abort as default_abort
from flask_restx.fields import List as ListField, Boolean as BoolField, Nested
from flask_restx.marshalling import marshal
from flask_restx.reqparse import RequestParser

from main import Session, Base, index_service
from common._whoosh import Searcher
from ._marshals import ResponseDoc, success_response, message_response


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
    def find_by_id(cls, session: Session, entry_id: int) -> Union[Identifiable, None]:
        raise NotImplementedError


class UserRole(Identifiable):
    """
    An interface to mark database classes as user roles, that can be used for authorization.

    Used in :ref:`.Namespace.jwt_authorizer`
    """

    default_role: Union[UserRole, None] = None

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> Union[UserRole, None]:
        raise NotImplementedError


def get_or_pop(dictionary: dict, key, keep: bool = False):
    return dictionary[key] if keep else dictionary.pop(key)


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


class _Namespace(RestXNamespace):  # for the lib
    """
    Expansion of :class:`RestXNamespace`, which adds decorators for methods of :class:`Resource`.

    Methods of this class (used as decorators) allow parsing request parameters,
    modifying responses and automatic updating Swagger documentation where possible
    """

    def abort(self, code: int, message: str = None, **kwargs):
        default_abort(code, message, **kwargs)

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

    def database_searcher(self, identifiable: Type[Identifiable], *, result_field_name: Union[str, None] = None,
                          check_only: bool = False, use_session: bool = False):
        """
        - Uses incoming id argument to find something :class:`Identifiable` in the database.
        - If the entity wasn't found, will return a 404 response, which is documented automatically.
        - Can pass (entity's id or entity) and session objects to the decorated function.

        :param identifiable: identifiable to search for
        :param result_field_name: overrides default name of found object [default is identifiable.__name__.lower()]
        :param check_only: (default: False) if True, checks if entity exists and passes id to the decorated function
        :param use_session: (default: False) whether to pass the session to the decorated function
        """

        def searcher_wrapper(function):
            @self.response(*ResponseDoc.error_response("404 ", identifiable.not_found_text).get_args())
            @wraps(function)
            @with_session
            def searcher_inner(*args, **kwargs):
                return self._database_searcher(identifiable, check_only, False, use_session, 404,
                                               function, args, kwargs, result_field_name=result_field_name)

            return searcher_inner

        return searcher_wrapper

    auth_errors: list[ResponseDoc] = [
        ResponseDoc.error_response("401 ", "JWTError"),
        ResponseDoc.error_response("422 ", "InvalidJWT")
    ]

    def jwt_authorizer(self, role: Type[UserRole], optional: bool = False,
                       check_only: bool = False, use_session: bool = True):
        """
        - Authorizes user by JWT-token.
        - If token is missing or is not processable, falls back on flask-jwt-extended error handlers.
        - If user doesn't exist or doesn't have the role required, sends the corresponding response.
        - All error responses are added to the documentation automatically.
        - Can pass user and session objects to the decorated function.

        :param role: role to expect
        :param optional: (default: False)
        :param check_only: (default: False) if True, user object won't be passed to the decorated function
        :param use_session: (default: True) whether to pass the session to the decorated function
        """

        def authorizer_wrapper(function):
            error_code: int = 401 if role is UserRole.default_role else 403

            @self.doc_responses(ResponseDoc.error_response(f"{error_code} ", role.not_found_text), *self.auth_errors)
            @self.doc(security="jwt")
            @wraps(function)
            @jwt_required(optional=optional)
            @with_session
            def authorizer_inner(*args, **kwargs):
                if (jwt := get_jwt_identity()) is None and optional:
                    kwargs[role.__name__.lower()] = None
                    return function(*args, **kwargs)
                kwargs["jwt"] = jwt
                return self._database_searcher(role, check_only, True, use_session, error_code,
                                               function, args, kwargs, input_field_name="jwt")

            return authorizer_inner

        return authorizer_wrapper

    def doc_file_param(self, field_name: str):  # redo...
        def doc_file_param_wrapper(function):
            return self.doc(**{
                "params": {field_name: {"in": "formData", "type": "file"}},
                "consumes": "multipart/form-data"
            })(function)

        return doc_file_param_wrapper

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

    def lister(self, per_request: int, marshal_model: Model, skip_none: bool = True):
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
        :return:
        """
        response = ResponseDoc(200, f"Max size of results: {per_request}", Model(f"List" + marshal_model.name, {
            "results": ListField(Nested(marshal_model), max_items=per_request), "has-next": BoolField}))

        def lister_wrapper(function):
            @self.doc_responses(response)
            @wraps(function)
            def lister_inner(*args, **kwargs):
                offset: int = kwargs.pop("offset", None)
                counter: int = kwargs.pop("counter", None)
                if offset is None:
                    if counter is None:
                        self.abort(400, "Neither counter nor offset are provided")
                    offset = counter * per_request

                kwargs["start"] = offset
                kwargs["finish"] = offset + per_request + 1
                result_list = function(*args, **kwargs)

                if has_next := len(result_list) > per_request:
                    result_list.pop()

                return {"results": marshal(result_list, marshal_model, skip_none=skip_none), "has-next": has_next}

            return lister_inner

        return lister_wrapper


class Namespace(_Namespace):  # xi-effect specific
    def abort(self, code: int, message: str = None, **kwargs):
        default_abort(code, a=message, **kwargs)


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