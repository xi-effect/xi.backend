from __future__ import annotations

from flask_restx import Model
from flask_restx.fields import Boolean as BooleanField, String as StringField

from flask_fullstack import ResponseDoc as _ResponseDoc


class ResponseDoc(_ResponseDoc):
    @classmethod
    def error_response(cls, code: int | str, description: str) -> ResponseDoc:
        """Creates an instance of an :class:`ResponseDoc` with a message response model for the response body"""
        return cls(code, description, Model("Message Response", {"a": StringField}))


success_response: ResponseDoc = ResponseDoc(
    model=Model("Default Response", {"a": BooleanField})
)  # noqa: WPS462
"""Default success response representation ({"a": :class:`bool`})"""  # noqa: WPS428, WPS322
message_response: ResponseDoc = ResponseDoc(
    model=Model("Message Response", {"a": StringField})
)  # noqa: WPS462
"""Default message response representation ({"a": :class:`str`})"""  # noqa: WPS322, WPS428
