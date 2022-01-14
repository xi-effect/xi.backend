from __future__ import annotations

from typing import Union

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, JSON, DateTime, Text, Enum

from common import Identifiable, Marshalable, LambdaFieldDef, create_marshal_model, register_as_searchable, TypeEnum
from main import Base, Session


class TestResult(Base):
    # id PK
    # user_id FK
    # module_id FK
    # short_result (JSON)
    # result (JSON)

    # create
    # find_by_id
    # find_by_user
    pass
