from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from flask_fullstack import Identifiable, PydanticModel, TypeEnum, JSONWithModel
from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, JSON, DateTime, Text, Enum

from common import Base, User, db


class TABLE(Base):
    __tablename__ = "..."

    pass
