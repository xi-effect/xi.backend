from abc import ABC
from string import Template
from typing import Any, Dict, List, Tuple


class Variable:
    templatable_keys: List[str] = []

    @classmethod
    def generate_raw(cls, data: Dict[str, Any]) -> Any:
        raise NotImplementedError  # makeup a better name

    @classmethod
    def generate_formatted(cls, data: Dict[str, Any]) -> Tuple[Any, str]:
        raw = cls.generate_raw(data)
        return raw, str(raw)

    @classmethod
    def generate(cls, var_data: Dict[str, Any], req_data: Dict[str, Any]) -> Tuple[Any, str]:
        var_data.update({key: Template(var_data[temp_key]).substitute(req_data)
                         for key in cls.templatable_keys
                         if (temp_key := "$" + key) in var_data.keys()})
        return cls.generate_formatted(var_data)


class NumericVariable(Variable, ABC):
    templatable_keys = ["format"]  # ???

    @classmethod
    def generate_formatted(cls, data: Dict[str, Any]) -> Tuple[Any, str]:
        if "format" in data.keys():
            number_format = data["format"]
            raw = cls.generate_raw(data)
            return raw, f"{raw:{number_format}}"
        else:
            return super().generate_formatted(data)
