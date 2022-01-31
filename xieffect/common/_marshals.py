from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from json import loads as json_loads
from typing import Type, Union, get_type_hints, Callable

from flask_restx import Model, Namespace
from flask_restx.fields import (Raw as RawField, Boolean as BooleanField,
                                Integer as IntegerField, String as StringField)
from sqlalchemy import Column, Sequence, Enum
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import Boolean, Integer, String, JSON, DateTime

from ._utils import TypeEnum


class EnumField(StringField):
    def format(self, value: TypeEnum) -> str:
        return value.to_string()


class DateTimeField(StringField):
    def format(self, value: datetime) -> str:
        return value.isoformat()


class JSONLoadableField(RawField):
    def format(self, value: str) -> list:
        return json_loads(value)


type_to_field: dict[type, Type[RawField]] = {
    bool: BooleanField,
    int: IntegerField,
    str: StringField,
    JSON: JSONLoadableField,
    datetime: DateTimeField,
}

column_to_field: dict[Type[TypeEngine], Type[RawField]] = {
    Integer: IntegerField,
    String: StringField,
    Boolean: BooleanField,
    JSON: JSONLoadableField,
    DateTime: DateTimeField,
    Enum: EnumField
}


@dataclass()
class LambdaFieldDef:
    """
    A field to be used in create_marshal_model, which can't be described as a :class:`Column`.

    - model_name — global name of the model to connect the field to.
    - field_type — field's return type (:class:`bool`, :class:`int`, :class:`str` or :class:`datetime`).
    - attribute — the attribute to pass to the field's keyword argument ``attribute``.
      can be a :class:`Callable` that uses models pre-marshalled version.
    """

    model_name: str
    field_type: type
    attribute: Union[str, Callable]
    name: Union[str, None] = None

    def to_field(self) -> Union[Type[RawField], RawField]:
        field_type: Type[RawField] = RawField
        for supported_type in type_to_field:
            if issubclass(self.field_type, supported_type):
                field_type = type_to_field[supported_type]
                break
        return field_type(attribute=self.attribute)


def create_marshal_model(model_name: str, *fields: str, inherit: Union[str, None] = None, use_defaults: bool = False):
    """
    - Adds a marshal model to a database object, marked as :class:`Marshalable`.
    - Automatically adds all :class:`LambdaFieldDef`-marked class fields to the model.
    - Sorts modules keys by alphabet and puts ``id`` field on top if present.

    :param model_name: the **global** name for the new model or model to be overwritten.
    :param fields: filed names of columns to be added to the model.
    :param inherit: model name to inherit fields from.
    :param use_defaults: whether to describe columns' defaults in the model.
    """

    def create_marshal_model_wrapper(cls):
        def create_field(column: Column, column_type: Type[TypeEngine]):
            field_type: Type[RawField] = column_to_field[column_type]

            if not use_defaults or column.default is None or column.nullable or isinstance(column.default, Sequence):
                return field_type(attribute=column.name)
            else:
                return field_type(attribute=column.name, default=column.default.arg)

        model_dict = {} if inherit is None else cls.marshal_models[inherit].copy()

        model_dict.update({
            column.name.replace("_", "-"): create_field(column, supported_type)
            for column in cls.__table__.columns
            if column.name in fields
            for supported_type in column_to_field.keys()
            if isinstance(column.type, supported_type)
        })

        model_dict.update({
            field_name.replace("_", "-") if field.name is None else field.name: field.to_field()
            for field_name, field_type in get_type_hints(cls).items()
            if isinstance(field_type, type) and issubclass(field_type, LambdaFieldDef)
            if (field := getattr(cls, field_name)).model_name == model_name
        })

        cls.marshal_models[model_name] = OrderedDict(sorted(model_dict.items()))
        if "id" in cls.marshal_models[model_name].keys():
            cls.marshal_models[model_name].move_to_end("id", last=False)

        return cls

    return create_marshal_model_wrapper


class Marshalable:
    """ Marker-class for classes that can be decorated with ``create_marshal_model`` """
    marshal_models: dict[str, OrderedDict[str, Type[RawField]]] = {}


def unite_models(*models: dict[str, Union[Type[RawField], RawField]]):
    """
    - Unites several field dicts (models) into one.
    - If some fields are present in more than one model, the last encounter will be used.
    - Sorts modules keys by alphabet and puts ``id`` field on top if present.

    :param models: models (dicts of field definitions) to unite
    :return: united model with all fields
    """

    model_dict: OrderedDict = OrderedDict()
    for model in models:
        model_dict.update(model)
    model_dict = OrderedDict(sorted(model_dict.items()))
    if "id" in model_dict.keys():
        model_dict.move_to_end("id", last=False)
    return model_dict


@dataclass()
class ResponseDoc:
    """ Dataclass to keep the response description is one place """

    code: Union[int, str] = 200
    description: str = None
    model: Union[Model, None] = None

    @classmethod
    def error_response(cls, code: Union[int, str], description: str) -> ResponseDoc:
        """ Creates an instance of an :class:`ResponseDoc` with a message response model for the response body """
        return cls(code, description, Model("Message Response", {"a": StringField}))

    def register_model(self, ns: Namespace):
        if self.model is not None:
            self.model = ns.model(self.model.name, self.model)

    def get_args(self) -> Union[tuple[Union[int, str], str], tuple[Union[int, str], str, Model]]:
        if self.model is None:
            return self.code, self.description
        return self.code, self.description, self.model


success_response: ResponseDoc = ResponseDoc(model=Model("Default Response", {"a": BooleanField}))
""" Default success response representation ({"a": :class:`bool`}) """
message_response: ResponseDoc = ResponseDoc(model=Model("Message Response", {"a": StringField}))
""" Default message response representation ({"a": :class:`str`}) """
