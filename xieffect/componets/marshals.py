from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from json import loads as json_loads
from typing import Type, Dict, Tuple, Union, Optional, Callable

from flask_restx import Model, Namespace
from flask_restx.fields import Raw as RawField, Boolean as BooleanField, Integer as IntegerField, String as StringField
from sqlalchemy import Column, Sequence
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import Boolean, Integer, String, JSON, DateTime
from sqlalchemy_enum34 import EnumType

from .other import TypeEnum


class EnumField(StringField):
    def format(self, value: TypeEnum) -> str:
        return value.to_string()


class DateTimeField(StringField):
    def format(self, value: datetime) -> str:
        return value.isoformat()


class JSONLoadableField(StringField):
    def format(self, value: str) -> str:
        return json_loads(value)


type_to_field: Dict[type, Type[RawField]] = {
    bool: BooleanField,
    int: IntegerField,
    str: StringField,
    datetime: DateTimeField,
}

column_to_field: Dict[Type[TypeEngine], Type[RawField]] = {
    Integer: IntegerField,
    String: StringField,
    Boolean: BooleanField,
    JSON: JSONLoadableField,
    DateTime: DateTimeField,
    EnumType: EnumField,
}


def create_field(field_type: Type[RawField], column: Column, ignore_defaults: bool = True):
    if ignore_defaults or column.default is None or column.nullable or isinstance(column.default, Sequence):
        return field_type(attribute=column.name)
    else:
        return field_type(attribute=column.name, default=column.default.arg)


@dataclass()
class LambdaFieldDef:
    model_name: str
    field_type: type
    attribute: Union[str, Callable]

    def to_field(self):
        field_type: Type[RawField] = RawField
        for supported_type in type_to_field:
            if issubclass(self.field_type, supported_type):
                field_type = type_to_field[supported_type]
                break
        return field_type(attribute=self.attribute)


def create_marshal_model(model_name: str, *fields: str, full: bool = False,
                         inherit: Optional[str] = None, use_defaults: bool = False):
    def create_marshal_model_wrapper(cls):
        model_dict = {} if inherit is None else cls.marshal_models[inherit].copy()

        model_dict.update({
            column.name.replace("_", "-"): create_field(column_to_field[supported_type], column, not use_defaults)
            for column in cls.__table__.columns
            if (column.name in fields) != full
            for supported_type in column_to_field.keys()
            if isinstance(column.type, supported_type)
        })

        model_dict.update({
            field_name.replace("_", "-"): field.to_field()
            for field_name, field_type in cls.__dict__.get('__annotations__', {}).items()
            if issubclass(field_type, LambdaFieldDef)
            if (field := getattr(cls, field_name)).model_name == model_name
        })

        cls.marshal_models[model_name] = OrderedDict(sorted(model_dict.items()))
        if "id" in cls.marshal_models[model_name].keys():
            cls.marshal_models[model_name].move_to_end("id", last=False)

        return cls

    return create_marshal_model_wrapper


class Marshalable:
    marshal_models: Dict[str, OrderedDict[str, Type[RawField]]] = {}


def unite_models(*models):
    model_dict: OrderedDict = OrderedDict()
    for model in models:
        model_dict.update(model)
    model_dict = OrderedDict(sorted(model_dict.items()))
    if "id" in model_dict.keys():
        model_dict.move_to_end("id", last=False)
    return model_dict


@dataclass()
class ResponseDoc:
    code: int = 200
    description: str = None
    model: Optional[Model] = None

    @classmethod
    def error_response(cls, code: int, description: str):
        return cls(code, description, Model("Message Response", {"a": StringField}))

    def register_model(self, ns: Namespace):
        if self.model is not None:
            self.model = ns.model(self.model.name, self.model)

    def get_args(self) -> Union[Tuple[int, str], Tuple[int, str, Model]]:
        if self.model is None:
            return self.code, self.description
        return self.code, self.description, self.model


success_response: ResponseDoc = ResponseDoc(model=Model("Default Response", {"a": BooleanField}))
message_response: ResponseDoc = ResponseDoc(model=Model("Message Response", {"a": StringField}))
