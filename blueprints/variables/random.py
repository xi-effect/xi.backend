from random import randint
from typing import Dict, Any, List

from .base import Variable


class RandomIntegerVar(Variable):
    templatable_keys: List[str] = ["min", "max"]

    @classmethod
    def _generate(cls, data: Dict[str, Any]) -> int:
        return randint(*map(int, (data["min"], data["max"])))
