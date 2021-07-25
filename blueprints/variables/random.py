from random import randint
from typing import Dict, Any, List

from .base import NumericVariable


class RandomIntegerVar(NumericVariable):
    templatable_keys: List[str] = ["min", "max"]

    @classmethod
    def generate_raw(cls, data: Dict[str, Any]) -> Any:
        return randint(*map(int, (data["min"], data["max"])))
