from __future__ import annotations

import warnings
from typing import Self

import pydantic as pydantic_v2
import pydantic.v1 as pydantic_v1  # noqa: WPS301
from flask_fullstack import PydanticModel
from pydantic_core import PydanticUndefined


def v2_field_to_v1(field: pydantic_v2.fields.FieldInfo) -> pydantic_v1.fields.FieldInfo:
    kwargs = {"alias": field.alias}
    if field.default is not PydanticUndefined:
        kwargs["default"] = field.default
    return pydantic_v1.Field(**kwargs)


class PydanticBase(PydanticModel):
    class Config:
        orm_mode = True

    @classmethod
    def convert_one(cls, orm_object, **context) -> Self:
        if context:
            warnings.warn("Context is deprecated", DeprecationWarning)
        return cls.from_orm(orm_object)


def v2_model_to_v1(model: type[pydantic_v2.BaseModel]) -> type[PydanticModel]:
    return pydantic_v1.create_model(
        model.__name__,
        __base__=PydanticBase,
        **{
            f_name: (field.annotation, v2_field_to_v1(field))
            for f_name, field in model.model_fields.items()
        },
    )


def v2_model_to_ffs(model: type[pydantic_v2.BaseModel]) -> type[PydanticModel]:
    result = v2_model_to_v1(model)
    result.name = model.__name__
    return result
