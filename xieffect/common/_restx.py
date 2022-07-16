from __future__ import annotations

from functools import wraps
from typing import Type

from flask_restx import abort as default_abort

from __lib__.flask_fullstack import ResourceController
from ._marshals import success_response, message_response


class Namespace(ResourceController):  # xieffect specific
    from ._core import sessionmaker

    def __init__(self, *args, **kwargs):
        kwargs["sessionmaker"] = kwargs.get("sessionmaker", self.sessionmaker)
        super().__init__(*args, **kwargs)

    def abort(self, code: int, message: str = None, **kwargs):
        default_abort(code, a=message, **kwargs)

    def a_response(self):
        """
        - Wraps Resource's method return with ``{"a": <something>}`` response and updates documentation.
        - Defines response type automatically by looking at method's return type annotation.
        - If the return type is not specified, assumes None!
        """

        def a_response_wrapper(function):
            return_type: Type = getattr(function, "__annotations__").get("return", None)
            is_bool = return_type is None or issubclass(return_type, bool)

            @self.response(*(success_response if is_bool else message_response).get_args())
            @wraps(function)
            def a_response_inner(*args, **kwargs):
                result = function(*args, **kwargs)
                return {"a": True if return_type is None else result}

            return a_response_inner

        return a_response_wrapper


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
