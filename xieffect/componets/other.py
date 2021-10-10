from enum import Enum


class TypeEnum(Enum):
    @classmethod
    def from_string(cls, string: str):
        return cls.__members__[string.upper().replace("-", "_")]

    @classmethod
    def get_all_field_names(cls):
        return [member.lower().replace("_", "-") for member in cls.__members__]

    def to_string(self) -> str:
        return self.name.lower().replace("_", "-")
