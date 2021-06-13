from typing import Type, Optional, Union, Tuple, Callable, Any

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful.reqparse import RequestParser

from database import User, UserRole, Identifiable
from api_resources.base.parsers import counter_parser


def jwt_authorizer(role: Type[UserRole], result_filed_name: Optional[str] = "user"):
    def authorizer_wrapper(function):
        @jwt_required()
        def authorizer_inner(*args, **kwargs):
            result: role = role.find_by_id(get_jwt_identity())
            if result is None:
                return {"a": role.not_found_text}, 401 if role is User else 403
            else:
                if result_filed_name is not None:
                    kwargs[result_filed_name] = result
                return function(*args, **kwargs)

        return authorizer_inner

    return authorizer_wrapper


def database_searcher(identifiable: Type[Identifiable], input_field_name: str,
                      result_filed_name: Optional[str] = None, check_only: bool = False):
    def searcher_wrapper(function):
        error_response: tuple = {"a": identifiable.not_found_text}, 404

        def searcher_inner(*args, **kwargs):
            target_id: int = kwargs.pop(input_field_name)
            result: identifiable = identifiable.find_by_id(target_id)
            if result is None:
                return error_response
            else:
                if result_filed_name is not None:
                    kwargs[result_filed_name] = result
                return function(*args, **kwargs)

        def checker_inner(*args, **kwargs):
            if identifiable.find_by_id(kwargs[input_field_name]) is None:
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


def lister(user_role: Type[UserRole], per_request: int, user_filed_name: Optional[str],
           argument_parser: Callable[[Callable], Any] = argument_parser(counter_parser, "counter")):
    def lister_wrapper(function):
        @jwt_authorizer(user_role)
        @argument_parser
        def lister_inner(*args, **kwargs):
            counter: int = kwargs.pop("counter") * per_request
            if user_filed_name is not None:
                kwargs[user_filed_name] = kwargs.pop("user")
            kwargs["start"] = counter
            kwargs["finish"] = counter + per_request
            return function(*args, **kwargs)

        return lister_inner

    return lister_wrapper
