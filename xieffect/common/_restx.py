from __future__ import annotations

from functools import wraps

from flask_restx import abort as default_abort

from __lib__.flask_fullstack import ResourceController as _ResourceController
from ._marshals import success_response, message_response  # noqa: WPS436


class ResourceController(_ResourceController):
    from ._core import sessionmaker  # noqa: WPS436

    def __init__(self, *args, **kwargs):
        kwargs["sessionmaker"] = kwargs.get("sessionmaker", self.sessionmaker)
        super().__init__(*args, **kwargs)
        success_response.register_model(self)
        message_response.register_model(self)

    def abort(self, code: int, message: str = None, **kwargs):
        default_abort(code, a=message, **kwargs)

    def a_response(self):
        """
        - Wraps Resource's method return with ``{"a": <something>}`` response and updates documentation.
        - Defines response type automatically by looking at method's return type annotation.
        - If the return type is not specified, assumes None!
        """

        def a_response_wrapper(function):
            return_type = function.__annotations__.get("return", None)
            is_none = return_type is None or return_type == "None"
            is_bool = (
                is_none
                or return_type == "bool"
                or (isinstance(return_type, type) and issubclass(return_type, bool))
            )

            @self.response(
                *(success_response if is_bool else message_response).get_args()
            )
            @wraps(function)
            def a_response_inner(*args, **kwargs):
                result = function(*args, **kwargs)
                return {"a": True if is_none else result}

            return a_response_inner

        return a_response_wrapper
