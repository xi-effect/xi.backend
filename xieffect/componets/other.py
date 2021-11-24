from __future__ import annotations

from enum import Enum
from typing import Optional


class TypeEnum(Enum):
    @classmethod
    def from_string(cls, string: str) -> Optional[TypeEnum]:
        return cls.__members__.get(string.upper().replace("-", "_"), None)

    @classmethod
    def get_all_field_names(cls) -> list[str]:
        return [member.lower().replace("_", "-") for member in cls.__members__]

    @classmethod
    def form_whens(cls) -> list[tuple[str, int]]:
        return [(name, value.value) for name, value in cls.__members__.items()]

    def to_string(self) -> str:
        return self.name.lower().replace("_", "-")
