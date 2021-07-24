from typing import Dict, Any

from .base import Variable


class Residue(Variable):
    templatable_keys = ["expression"]
    globals: Dict[str, Any] = {}

    @classmethod
    def _generate(cls, data: Dict[str, Any]) -> Any:
        return eval(data["expression"], cls.globals)  # can give a SyntaxError
