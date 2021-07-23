from string import Template
from typing import Any, Dict, List


class Variable:
    templatable_keys: List[str] = []

    @classmethod
    def _generate(cls, data: Dict[str, Any]) -> Any:  # makeup a better name
        raise NotImplementedError

    @classmethod
    def generate(cls, var_data: Dict[str, Any], req_data: Dict[str, Any]) -> Any:
        var_data.update({key: Template(var_data[temp_key]).substitute(req_data)
                         for key in cls.templatable_keys
                         if (temp_key := "$" + key) in var_data.keys()})
        return cls._generate(var_data)
