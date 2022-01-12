import math
import re
from typing import Dict, Any

from .base import Variable


class Residue(Variable):
    templatable_keys = ["expression"]
    globals: Dict[str, Any] = {}

    @classmethod
    def generate_raw(cls, data: Dict[str, Any]) -> Any:
        return eval(data["expression"], cls.globals)  # can give a SyntaxError


class MathResidue(Residue):
    globals = {"math": math}


class RegexResidue(Residue):
    globals = {func.__name__: func for func in (re.sub,)}
