from enum import Enum


class Type(Enum):
    @classmethod
    def from_string(cls, string: str):
        return cls.__members__[string.upper()]

    def to_string(self) -> str:
        return self.name.lower()
