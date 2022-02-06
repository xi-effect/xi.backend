from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from typing import Type, Union, get_type_hints, Callable

from flask_restx import Model, Namespace
from flask_restx.fields import (Raw as RawField, Nested as NestedField, List as ListField,
                                Boolean as BooleanField, Integer as IntegerField, String as StringField)
from sqlalchemy import Column, Sequence, Enum
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import Boolean, Integer, String, JSON, DateTime

from .sqlalchemy import JSONWithModel
from .utils import TypeEnum

flask_restx_has_bad_design: Namespace = Namespace("this-is-dumb")


class EnumField(StringField):
    def format(self, value: TypeEnum) -> str:
        return value.to_string()


class DateTimeField(StringField):
    def format(self, value: datetime) -> str:
        return value.isoformat()


class JSONLoadableField(RawField):
    # TODO https://docs.sqlalchemy.org/en/14/core/type_basics.html#sqlalchemy.types.JSON
    def format(self, value):
        return value


# class ConfigurableField:
#     @classmethod
#     def create(cls, column: Column, column_type: Union[Type[TypeEngine], TypeEngine],
#                default=None) -> Union[RawField, Type[RawField]]:
#         raise NotImplementedError


class JSONWithModelField:  # (ConfigurableField):
    # @classmethod
    # def create(cls, column: Column, *_) -> RawField:
    #     field = NestedField(flask_restx_has_bad_design.model(column.type.model_name, column.type.model))
    #     if column.type.as_list:
    #         return ListField(field)
    #     return field
    pass


# class JSONWithSchemaField(ConfigurableField):
#     @classmethod
#     def create(cls, column: Column, column_type: JSONWithSchema, default=None) -> Type[JSONLoadableField]:
#         class JSONField(JSONLoadableField):
#             __schema_type__ = column.type.schema_type
#             __schema_format__ = column.type.schema_format  # doesn't work!
#             __schema_example__ = column.type.schema_example or default
#
#         return JSONField


type_to_field: dict[type, Type[RawField]] = {
    bool: BooleanField,
    int: IntegerField,
    str: StringField,
    JSON: JSONLoadableField,
    datetime: DateTimeField,
}

column_to_field: dict[Type[TypeEngine], Type[RawField]] = {
    JSONWithModel: JSONWithModelField,
    JSON: JSONLoadableField,
    DateTime: DateTimeField,
    Enum: EnumField,
    Boolean: BooleanField,
    Integer: IntegerField,
    String: StringField,
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


def create_marshal_model(model_name: str, *fields: str, inherit: Union[str, None] = None,
                         use_defaults: bool = False, flatten_jsons: bool = False):
    """
    - Adds a marshal model to a database object, marked as :class:`Marshalable`.
    - Automatically adds all :class:`LambdaFieldDef`-marked class fields to the model.
    - Sorts modules keys by alphabet and puts ``id`` field on top if present.
    - Uses kebab-case for json-names. TODO allow different cases

    :param model_name: the **global** name for the new model or model to be overwritten.
    :param fields: filed names of columns to be added to the model.
    :param inherit: model name to inherit fields from.
    :param use_defaults: whether to describe columns' defaults in the model.
    :param flatten_jsons: whether to put inner JSON fields in the root model or as a Nested field
    """

    def create_marshal_model_wrapper(cls):
        def move_field_attribute(root_name: str, field_name: str, field_def: Union[Type[RawField], RawField]):
            attribute_name: str = f"{root_name}.{field_name}"
            if isinstance(field_def, type):
                return field_def(attribute=attribute_name)
            field_def.attribute = attribute_name
            return field_def

        def create_fields(column: Column, column_type: Union[Type[TypeEngine], TypeEngine]) -> dict[str, ...]:
            if not use_defaults or column.default is None or column.nullable or isinstance(column.default, Sequence):
                default = None
            else:
                default = column.default.arg

            field_type: Type[RawField] = column_to_field[column_type]
            if issubclass(field_type, JSONWithModelField):
                if flatten_jsons and not column.type.as_list:
                    root_name: str = column.name.replace("_", "-")
                    return {k: move_field_attribute(root_name, k, v) for k, v in column.type.model.items()}
                field = NestedField(flask_restx_has_bad_design.model(column.type.model_name, column.type.model))
                if column.type.as_list:
                    field = ListField(field)
                # field: RawField = field_type.create(column, column_type, default)
            else:
                field = field_type(attribute=column.name, default=default)

            return {column.name.replace("_", "-"): field}

        def detect_field_type(column):
            for supported_type in column_to_field.keys():
                if isinstance(column.type, supported_type):
                    return supported_type

        model_dict = {} if inherit is None else cls.marshal_models[inherit].copy()

        model_dict.update({
            k: v
            for column in cls.__table__.columns
            if column.name in fields
            if (field_type := detect_field_type(column)) is not None
            for k, v in create_fields(column, field_type).items()
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
        return cls(code, description)

    def register_model(self, ns: Namespace):
        if self.model is not None:
            self.model = ns.model(self.model.name, self.model)

    def get_args(self) -> Union[tuple[Union[int, str], str], tuple[Union[int, str], str, Model]]:
        if self.model is None:
            return self.code, self.description
        return self.code, self.description, self.model
