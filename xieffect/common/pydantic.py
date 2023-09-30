from __future__ import annotations

import warnings
from typing import Self, Any, get_origin, get_args, ClassVar

import pydantic as pydantic_v2
import pydantic.v1 as pydantic_v1  # noqa: WPS301
from flask_fullstack import PydanticModel
from pydantic_core import PydanticUndefined
from pydantic_marshals.utils import is_subtype


def v2_annotation_to_v1(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is list and is_subtype(get_args(annotation)[0], pydantic_v2.BaseModel):
        return list[v2_model_to_ffs(get_args(annotation)[0])]
    if is_subtype(annotation, pydantic_v2.BaseModel):
        return v2_model_to_ffs(annotation)
    return annotation


def v2_field_to_v1(field: pydantic_v2.fields.FieldInfo) -> pydantic_v1.fields.FieldInfo:
    kwargs = {"alias": field.alias}
    if field.default is not PydanticUndefined:
        kwargs["default"] = field.default
    return pydantic_v1.Field(**kwargs)


class PydanticBase(PydanticModel):
    raw: ClassVar[type[pydantic_v2.BaseModel]]

    class Config:
        orm_mode = True

    @classmethod
    def convert_one(cls, orm_object, **context) -> Self:
        if context:
            warnings.warn("Context is deprecated", DeprecationWarning)
        return cls.from_orm(orm_object)


def v2_model_to_ffs(model: type[pydantic_v2.BaseModel]) -> type[PydanticBase]:
    result = pydantic_v1.create_model(
        model.__name__,
        __base__=PydanticBase,
        **{
            f_name: (v2_annotation_to_v1(field.annotation), v2_field_to_v1(field))
            for f_name, field in model.model_fields.items()
        },
    )
    result.name = model.__name__
    result.raw = model
    return result
