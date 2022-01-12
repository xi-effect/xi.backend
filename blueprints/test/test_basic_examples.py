from re import sub

from engine import render, render_json_file


def render_math_equation():
    return render("0.0.1",
                  {"x": {"type": "random-integer", "min": -100, "max": 0},
                   "p": {"type": "residue", "$expression": "$x * (-2)"},
                   "q": {"type": "residue", "$expression": "($x) ** 2"}},
                  "{\"task\": \"Найдите корень уравнения: x**2 + ${p}x + $q = 0\", \"answer\": \"$x\"}")


def test_math_equation():
    temp = (render_json_file("blueprints/test/samples/math001.json"), render_math_equation())
    temp = tuple(map(lambda x: sub(r"\d", "", x), temp))
    assert temp[0] == temp[1]
