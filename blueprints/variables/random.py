from random import randint
from typing import Dict, Any, List

from .base import NumericVariable, Variable


class RandomBoolean(Variable):
    @classmethod
    def generate_raw(cls, data: Dict[str, Any]) -> bool:
        return bool(randint(0, 1))


class RandomInteger(NumericVariable):
    templatable_keys: List[str] = ["min", "max"]

    @classmethod
    def generate_raw(cls, data: Dict[str, Any]) -> int:
        return randint(*map(int, (data["min"], data["max"])))


class RandomDecimal(NumericVariable):
    templatable_keys: List[str] = ["min", "max", "precision"]

    @classmethod
    def generate_raw(cls, data: Dict[str, Any]) -> float:
        return randint(*map(int, (data["min"], data["max"]))) / 10 ** int(data["precision"])


class RandomArray(Variable):
    templatable_keys: List[str] = ["values", "size"]

    @classmethod
    def generate_raw(cls, data: Dict[str, Any]) -> Any:  # unsafe eval
        return eval(data["list"])[randint(0, int(data["size"]) - 1)]


class RandomList(Variable):
    templatable_keys: List[str] = ["values"]

    @classmethod
    def generate_raw(cls, data: Dict[str, Any]) -> Any:  # unsafe eval
        list_data: list = eval(data["values"])
        return list_data[randint(0, len(list_data) - 1)]
