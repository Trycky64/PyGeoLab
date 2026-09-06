"""Exercise actual object recipes against the pure geometry engine."""

from dataclasses import FrozenInstanceError, replace

import pytest

from pygeolab.geometry import Circle2D, Line2D, Point2D, Segment2D
from pygeolab.model.constructions import evaluate
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style


def point(name: str, x: float, y: float) -> GeoObject:
    """Create an evaluated point parent without requiring document orchestration."""
    return GeoObject("point", name, params={"x": x, "y": y}, geometry=Point2D(x, y))


@pytest.mark.parametrize(
    "kind",
    [
        "segment",
        "line",
        "ray",
        "vector",
        "circle",
        "midpoint",
        "perpendicular_bisector",
        "distance",
    ],
)
def test_two_point_recipes(kind: str) -> None:
    assert evaluate(GeoObject(kind, "object"), (point("A", 0, 0), point("B", 4, 0))) is not None


def test_chained_segment_midpoint_circle_recipe() -> None:
    a, b = point("A", 0, 0), point("B", 4, 0)
    segment = GeoObject("segment", "s", (a.id, b.id))
    segment = replace(segment, geometry=evaluate(segment, (a, b)))
    middle = GeoObject("midpoint", "M", (segment.id,))
    middle = replace(middle, geometry=evaluate(middle, (segment,)))
    circle = GeoObject("circle", "c", (middle.id, a.id))
    assert middle.geometry == Point2D(2, 0)
    assert evaluate(circle, (middle, a)) == Circle2D(Point2D(2, 0), 2)


def test_undefined_intersection_retains_definition() -> None:
    line_a = GeoObject("line", "d", geometry=Line2D(0, 1, 0))
    line_b = GeoObject("line", "e", geometry=Line2D(0, 1, 2))
    crossing = GeoObject("intersection", "I", (line_a.id, line_b.id))
    assert evaluate(crossing, (line_a, line_b)) is None
    assert crossing.dependencies == (line_a.id, line_b.id)


def test_point_on_and_projection_clamp_to_segment() -> None:
    support = GeoObject("segment", "s", geometry=Segment2D(Point2D(0, 0), Point2D(2, 0)))
    assert evaluate(GeoObject("point_on", "P", params={"t": 2}), (support,)) == Point2D(2, 0)
    assert evaluate(GeoObject("projection", "Q"), (point("A", 5, 1), support)) == Point2D(2, 0)


def test_three_point_recipes_and_transformations() -> None:
    a, b, c = point("A", 1, 0), point("B", 0, 0), point("C", 0, 1)
    for kind in ("polygon", "circumcircle", "angle", "angle_bisector"):
        assert evaluate(GeoObject(kind, "o"), (a, b, c)) is not None
    assert evaluate(GeoObject("reflect_point", "o"), (a, b)) == Point2D(-1, 0)
    assert evaluate(GeoObject("scale", "o", params={"factor": 3}), (a, b)) == Point2D(3, 0)


def test_identity_and_style_validation() -> None:
    obj = point("A", 0, 0)
    assert replace(obj, name="B").id == obj.id
    with pytest.raises(FrozenInstanceError):
        obj.id = "changed"
    for kwargs in ({"width": -1}, {"point_size": 0}, {"color": "red"}, {"line_style": "bad"}):
        with pytest.raises(ValueError):
            Style(**kwargs)
    with pytest.raises(ValueError):
        GeoObject("unknown", "A")
    with pytest.raises(ValueError):
        GeoObject("point", "")


def test_definition_parameters_are_copied_and_recursively_frozen() -> None:
    source = {"x": 1, "y": 2, "extra": {"values": [1, 2]}}
    obj = GeoObject("point", "A", params=source)
    source["x"] = 8
    source["extra"]["values"].append(3)
    assert obj.params["x"] == 1
    assert obj.params["extra"]["values"] == (1, 2)
    with pytest.raises(TypeError):
        obj.params["x"] = 4


def test_function_recipe_tracks_numeric_dependencies() -> None:
    parameter = GeoObject("number", "a", params={"value": 2.0}, geometry=2.0)
    function = GeoObject(
        "function",
        "f",
        dependencies=(parameter.id,),
        params={"variable": "x", "source": "sin(x) + a"},
    )
    geometry = evaluate(function, (parameter,))
    assert geometry is not None
    assert geometry.evaluate(0.0, {"a": 2.0}) == pytest.approx(2.0)
