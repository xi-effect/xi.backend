from json import load, loads, dumps
from typing import Type, Dict, Any
from string import Template

from variables import Variable, RandomBoolean, RandomInteger, RandomDecimal, RandomArray, RandomList
from variables import Residue, MathResidue, RegexResidue

with open("files/versions.json", "rb") as f:
    current_version: str = load(f)["BPE"]

var_types: Dict[str, Type[Variable]] = {
    # "undefined": Variable,
    "random-boolean": RandomBoolean,
    "random-integer": RandomInteger,
    "random-decimal": RandomDecimal,
    "random-array": RandomArray,
    "random-list": RandomList,
    "residue": Residue,
    "math-residue": MathResidue,
    "regex-residue": RegexResidue
}


def render(version: str, variables: Dict[str, Dict[str, Any]], content: str) -> str:
    # version check (improve if backward compatibility is broken)
    assert version <= current_version

    var_data: Dict[str, Any]
    raw_var_output: Dict[str, Any] = {}
    formatted_var_output: Dict[str, str] = {}
    for var_name, var_data in variables.items():
        var_output = var_types[var_data.pop("type")].generate(var_data, raw_var_output)
        raw_var_output[var_name] = var_output[0]
        formatted_var_output[var_name] = var_output[1]

    return Template(content).substitute(formatted_var_output)


def _render_json(json_data: dict) -> str:
    json_data["content"] = dumps(json_data["content"], ensure_ascii=False)
    return render(**json_data)


def render_json_string(json_string: str) -> str:
    return _render_json(loads(json_string))


def render_json_file(filename) -> str:
    with open(filename, "rb") as fp:
        return _render_json(load(fp))
