"""Verify explicit dependency graph operations and document dirty propagation."""

import pytest

from pygeolab.dependency import DependencyGraph
from pygeolab.geometry import Point2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style


def test_graph_supports_edges_descendants_and_topological_order() -> None:
    graph = DependencyGraph(("A", "B", "M", "C", "X"))
    graph.add_dependency("M", "A")
    graph.add_dependency("M", "B")
    graph.add_dependency("C", "M")

    assert graph.parents_of("M") == frozenset({"A", "B"})
    assert graph.children_of("M") == frozenset({"C"})
    assert graph.descendants({"A"}) == {"A", "M", "C"}
    order = graph.topological_order()
    assert order.index("A") < order.index("M") < order.index("C")
    assert order.index("B") < order.index("M")

    graph.remove_dependency("M", "B")
    assert graph.parents_of("M") == frozenset({"A"})


def test_graph_rejects_cycle_before_mutating_edges() -> None:
    graph = DependencyGraph(("A", "B", "C"))
    graph.add_dependency("B", "A")
    graph.add_dependency("C", "B")

    with pytest.raises(ValueError, match="cyclique"):
        graph.add_dependency("A", "C")

    assert graph.parents_of("A") == frozenset()
    assert graph.topological_order() == ("A", "B", "C")


def test_document_exposes_geometry_style_and_visibility_dirty_flags() -> None:
    document = Document()
    a = document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))
    b = document.add(GeoObject("point", "B", params={"x": 2, "y": 0}))
    midpoint = document.add(GeoObject("midpoint", "M", dependencies=(a.id, b.id)))

    document.move_point(a.id, Point2D(4, 0))
    assert set(document.last_recomputed) == {a.id, midpoint.id}
    assert document.last_dirty[a.id].geometry_dirty
    assert document.last_dirty[midpoint.id].geometry_dirty

    previous_midpoint = document.get(midpoint.id)
    document.update(a.id, style=Style(color="#ff0000"), visible=False)
    assert document.last_recomputed == ()
    assert document.last_dirty[a.id].style_dirty
    assert document.last_dirty[a.id].visibility_dirty
    assert document.get(midpoint.id) is previous_midpoint
