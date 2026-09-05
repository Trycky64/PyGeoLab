"""Verify slider variables and deterministic numerical-analysis algorithms."""

import math

import pytest

from pygeolab.geometry import Circle2D, Point2D
from pygeolab.math_engine.functions import FunctionObject
from pygeolab.math_engine.numerical import derivative, extrema, find_roots, integrate, intersections
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.variables import SliderSpec, numeric_variable, slider_spec


def test_slider_spec_validates_clamps_and_snaps() -> None:
    spec = SliderSpec(0.0, -1.0, 1.0, 0.25)
    assert spec.snapped(0.62) == pytest.approx(0.5)
    assert spec.snapped(9) == 1
    with pytest.raises(ValueError):
        SliderSpec(0, 1, -1, 0.1)
    with pytest.raises(ValueError):
        SliderSpec(0, -1, 1, 0)


def test_numeric_variable_recomputes_graph_dependents() -> None:
    document = Document()
    center = document.add(GeoObject("point", "O", params={"x": 0, "y": 0}))
    radius = document.add(numeric_variable("r", 2, 0, 10, 0.5))
    circle = document.add(GeoObject("circle_radius", "c", (center.id, radius.id)))
    assert circle.geometry == Circle2D(Point2D(0, 0), 2)
    document.update(radius.id, params={**radius.params, "value": 3.5})
    assert slider_spec(document.get(radius.id)).value == 3.5
    assert document.get(circle.id).geometry == Circle2D(Point2D(0, 0), 3.5)
    assert circle.id in document.last_recomputed


def test_derivative_and_simpson_integration() -> None:
    function = FunctionObject.from_source("f", "x", "x^3 - 2*x")
    assert derivative(function, 2) == pytest.approx(10, rel=1e-6)
    square = FunctionObject.from_source("g", "x", "x^2")
    assert integrate(square, 0, 3) == pytest.approx(9, rel=1e-10)
    assert integrate(square, 3, 0) == pytest.approx(-9, rel=1e-10)


def test_root_finder_skips_discontinuities_and_finds_brackets() -> None:
    function = FunctionObject.from_source("f", "x", "x^2 - 4")
    roots = find_roots(function, -5, 5)
    assert roots == pytest.approx((-2, 2), abs=1e-7)
    reciprocal = FunctionObject.from_source("r", "x", "1/x")
    assert find_roots(reciprocal, -1, 1) == ()


def test_extrema_and_function_intersections() -> None:
    parabola = FunctionObject.from_source("f", "x", "(x-2)^2 + 1")
    found = extrema(parabola, -2, 6)
    minimum = min(found, key=lambda item: item.y)
    assert minimum.kind == "minimum"
    assert minimum.x == pytest.approx(2, abs=1e-3)
    assert minimum.y == pytest.approx(1, abs=1e-6)

    line = FunctionObject.from_source("line", "x", "x")
    other = FunctionObject.from_source("other", "x", "2-x")
    point = intersections(line, other, -5, 5)[0]
    assert point == pytest.approx((1, 1), abs=1e-7)


def test_external_variables_work_in_numerical_analysis() -> None:
    function = FunctionObject.from_source("f", "x", "a*x")
    assert derivative(function, math.pi, {"a": 3}) == pytest.approx(3, rel=1e-6)
