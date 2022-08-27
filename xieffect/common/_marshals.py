from __future__ import annotations

from typing import Union

from flask_restx import Model
from flask_restx.fields import Boolean as BooleanField, String as StringField

from __lib__.flask_fullstack import ResponseDoc as _ResponseDoc


class ResponseDoc(_ResponseDoc):
    @classmethod
    def error_response(cls, code: Union[int, str], description: str) -> ResponseDoc:
        """Creates an instance of an :class:`ResponseDoc` with a message response model for the response body"""
        return cls(code, description, Model("Message Response", {"a": StringField}))


success_response: ResponseDoc = ResponseDoc(
    model=Model("Default Response", {"a": BooleanField})
)
""" Default success response representation ({"a": :class:`bool`}) """
message_response: ResponseDoc = ResponseDoc(
    model=Model("Message Response", {"a": StringField})
)
""" Default message response representation ({"a": :class:`str`}) """
