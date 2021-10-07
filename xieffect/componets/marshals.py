from datetime import datetime
from json import loads as json_loads
from typing import Type, Dict

from flask_restx.fields import Raw as RawField, Boolean as BooleanField, Integer as IntegerField, String as StringField
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import Boolean, Integer, String, JSON, DateTime
from sqlalchemy_enum34 import EnumType

from .other import TypeEnum


class EnumField(RawField):
    def format(self, value: TypeEnum) -> str:
        return value.to_string()


class DateTimeField(RawField):
    def format(self, value: datetime) -> str:
        return value.isoformat()


class JSONLoadableField(RawField):
    def format(self, value: str) -> str:
        return json_loads(value)


column_to_field: Dict[Type[TypeEngine], Type[RawField]] = {
    Integer: IntegerField,
    String: StringField,
    Boolean: BooleanField,
    JSON: JSONLoadableField,
    DateTime: DateTimeField,
    EnumType: EnumField
}


def create_marshal_model(model_name: str, *fields: str, full: bool = False):
    def create_marshal_model_wrapper(cls):
        cls.marshal_models[model_name] = {
            column.name.replace("_", "-"): column_to_field[supported_type]
            for column in cls.__table__.columns
            if (column.name in fields) != full
            for supported_type in column_to_field.keys()
            if isinstance(column.type, supported_type)
        }

        return cls

    return create_marshal_model_wrapper


class Marshalable:
    marshal_models: Dict[str, Dict[str, Type[RawField]]] = {}
