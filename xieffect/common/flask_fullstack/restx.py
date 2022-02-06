from __future__ import annotations

from functools import wraps
from typing import Union, Type

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Model, abort as default_abort
from flask_restx.fields import List as ListField, Boolean as BoolField, Nested
from flask_restx.marshalling import marshal
from flask_restx.reqparse import RequestParser

from .interfaces import Identifiable, UserRole
from .marshals import ResponseDoc
from .sqlalchemy import Sessionmaker
from .utils import get_or_pop


class RestXNamespace(Namespace):
    """
    Expansion of :class:`RestXNamespace`, which adds decorators for methods of :class:`Resource`.

    Methods of this class (used as decorators) allow parsing request parameters,
    modifying responses and automatic updating Swagger documentation where possible
    """

    def __init__(self, name: str, *, sessionmaker: Sessionmaker, description: str = None, path: str = None,
                 decorators=None, validate=None, authorizations=None, ordered: bool = False, **kwargs):
        super().__init__(name, description, path, decorators, validate, authorizations, ordered, **kwargs)
        self.with_begin = sessionmaker.with_begin
        self.with_autocommit = sessionmaker.with_autocommit

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
            @self.with_begin
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
            @self.with_begin
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

    def lister(self, per_request: int, marshal_model: Model, skip_none: bool = True):
        """
        - Used for organising pagination.
        - Uses `counter` form incoming arguments for the decorated function and `per_request` argument
          to define start and finish indexes, passed as keyword arguments to the decorated function.
        - Marshals the return of the decorated function as a list with `marshal_model`.
        - Adds information on the response to documentation automatically.

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
