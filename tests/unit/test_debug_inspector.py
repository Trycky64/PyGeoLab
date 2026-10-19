"""Comprehensive tests for PyGeoLab geometry object inspector and serialization."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pygeolab.data.dataset import DatasetObject
from pygeolab.debug.inspector import (
    RuntimeInspector,
    _sanitize_float,
    _sanitize_json_value,
    _serialize_geometry,
)
from pygeolab.debug.protocol import (
    DOCUMENT_REVISION_MISMATCH,
    INVALID_PARAMS,
    OBJECT_NOT_FOUND,
    ProtocolError,
)
from pygeolab.geometry.conics import Ellipse2D, Hyperbola2D, Parabola2D
from pygeolab.geometry.locus import Locus2D
from pygeolab.geometry.primitives import (
    Circle2D,
    Line2D,
    Point2D,
    Polygon2D,
    Ray2D,
    Segment2D,
    Vector2D,
)
from pygeolab.math_engine.functions import (
    FunctionObject,
    ParametricFunctionObject,
    PolarFunctionObject,
)
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject


class MockMainWindow(MagicMock):
    """Mock MainWindow for testing inspector methods."""

    def __init__(self, doc: Document | None = None) -> None:
        super().__init__()
        self.document = doc
        self.selection_coordinator = MagicMock()
        self.selection_coordinator.selected_ids = frozenset()


def test_sanitize_float_and_json() -> None:
    assert _sanitize_float(3.1415926) == 3.141593
    assert _sanitize_float(float("nan")) is None
    assert _sanitize_float(float("inf")) is None
    assert _sanitize_float(float("-inf")) is None

    sanitized = _sanitize_json_value(
        {
            "valid": 1.23,
            "nan": float("nan"),
            "nested": [1, float("inf"), "text", None, True],
        }
    )
    assert sanitized == {
        "valid": 1.23,
        "nan": None,
        "nested": [1.0, None, "text", None, True],
    }


def test_serialize_geometry_primitives() -> None:
    # Point2D
    geo, errs = _serialize_geometry(Point2D(1.0, 2.0))
    assert geo == {"type": "point", "x": 1.0, "y": 2.0}
    assert not errs

    # Segment2D
    geo, errs = _serialize_geometry(Segment2D(Point2D(0.0, 0.0), Point2D(3.0, 4.0)))
    assert geo == {
        "type": "segment",
        "start": {"x": 0.0, "y": 0.0},
        "end": {"x": 3.0, "y": 4.0},
        "length": 5.0,
    }
    assert not errs

    # Line2D
    line = Line2D(1.0, 0.0, -5.0)
    geo, errs = _serialize_geometry(line)
    assert geo == {"type": "line", "a": 1.0, "b": 0.0, "c": -5.0}
    assert not errs

    # Ray2D
    ray = Ray2D(Point2D(0.0, 0.0), Point2D(1.0, 1.0))
    geo, errs = _serialize_geometry(ray)
    assert geo == {
        "type": "ray",
        "start": {"x": 0.0, "y": 0.0},
        "through": {"x": 1.0, "y": 1.0},
    }
    assert not errs

    # Circle2D
    circ = Circle2D(Point2D(0.0, 0.0), 2.5)
    geo, errs = _serialize_geometry(circ)
    assert geo == {"type": "circle", "center": {"x": 0.0, "y": 0.0}, "radius": 2.5}
    assert not errs

    # Polygon2D
    poly = Polygon2D((Point2D(0.0, 0.0), Point2D(1.0, 0.0), Point2D(0.0, 1.0)))
    geo, errs = _serialize_geometry(poly)
    assert geo == {
        "type": "polygon",
        "vertices": [{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 0.0}, {"x": 0.0, "y": 1.0}],
        "vertex_count": 3,
    }
    assert not errs

    # Vector2D
    vec = Vector2D(3.0, 4.0)
    geo, errs = _serialize_geometry(vec)
    assert geo == {"type": "vector", "x": 3.0, "y": 4.0, "norm": 5.0}
    assert not errs

    # Scalar (float/int)
    geo, errs = _serialize_geometry(42.5)
    assert geo == {"type": "scalar", "value": 42.5}
    assert not errs


def test_serialize_geometry_conics_and_advanced() -> None:
    # Ellipse2D
    ellipse = Ellipse2D(Point2D(1.0, 2.0), a=5.0, b=3.0, angle=0.5)
    geo, errs = _serialize_geometry(ellipse)
    assert geo == {
        "type": "ellipse",
        "center": {"x": 1.0, "y": 2.0},
        "a": 5.0,
        "b": 3.0,
        "angle": 0.5,
    }
    assert not errs

    # Parabola2D
    parabola = Parabola2D(Point2D(0.0, 1.0), Line2D(0.0, 1.0, 1.0))
    geo, errs = _serialize_geometry(parabola)
    assert geo is not None
    assert geo["type"] == "parabola"
    assert "focus" in geo and "vertex" in geo and "parameter" in geo
    assert not errs

    # Hyperbola2D
    hyp = Hyperbola2D(Point2D(-2.0, 0.0), Point2D(2.0, 0.0), a=1.0)
    geo, errs = _serialize_geometry(hyp)
    assert geo == {
        "type": "hyperbola",
        "focus1": {"x": -2.0, "y": 0.0},
        "focus2": {"x": 2.0, "y": 0.0},
        "a": 1.0,
    }
    assert not errs

    # FunctionObject
    fn = FunctionObject.from_source("f", "x", "x^2", domain=(-10.0, 10.0))
    geo, errs = _serialize_geometry(fn)
    assert geo == {
        "type": "function",
        "name": "f",
        "variable": "x",
        "domain": [-10.0, 10.0],
    }
    assert not errs

    # ParametricFunctionObject
    param_fn = ParametricFunctionObject.from_source("curve", "t", "cos(t)", "sin(t)", 0.0, 6.28)
    geo, errs = _serialize_geometry(param_fn)
    assert geo == {
        "type": "parametric",
        "name": "curve",
        "parameter": "t",
        "t_min": 0.0,
        "t_max": 6.28,
    }
    assert not errs

    # PolarFunctionObject
    polar_fn = PolarFunctionObject.from_source("rose", "theta", "sin(2*theta)", 0.0, 6.28)
    geo, errs = _serialize_geometry(polar_fn)
    assert geo == {
        "type": "polar",
        "name": "rose",
        "parameter": "theta",
        "theta_min": 0.0,
        "theta_max": 6.28,
    }
    assert not errs

    # Locus2D
    locus = Locus2D((), "target-id", "driver-id", 0.0, 1.0, samples=100)
    geo, errs = _serialize_geometry(locus)
    assert geo == {
        "type": "locus",
        "target_id": "target-id",
        "driver_id": "driver-id",
        "segments_count": 0,
        "samples": 100,
    }
    assert not errs

    # DatasetObject
    ds = DatasetObject("test_data", column_names=("x", "y"), rows=((1.0, 2.0), (3.0, 4.0)))
    geo, errs = _serialize_geometry(ds)
    assert geo == {
        "type": "dataset",
        "name": "test_data",
        "column_names": ["x", "y"],
        "row_count": 2,
        "plot_kind": "scatter",
    }
    assert not errs

    # None and Unknown
    assert _serialize_geometry(None) == (None, [])
    geo_unk, _ = _serialize_geometry("a string")
    assert geo_unk == {"type": "unknown", "class": "str"}


def test_list_objects_empty_doc() -> None:
    doc = Document("Empty")
    mock_win = MockMainWindow(doc)
    inspector = RuntimeInspector(mock_win, start_time=0.0)

    res = inspector.list_objects()
    assert res["schema_version"] == "1.0.0"
    assert res["document_id"] == "Empty"
    assert res["document_revision"] == 0
    assert res["items"] == []
    assert res["returned_count"] == 0
    assert res["total_count"] == 0
    assert res["next_cursor"] is None
    assert not res["truncated"]


def test_list_objects_pagination_and_filtering() -> None:
    doc = Document("PaginationDoc")
    # Add 15 points
    for i in range(15):
        doc.add(GeoObject(kind="point", name=f"P_{i}", params={"x": float(i), "y": float(i)}))

    # Add 5 numbers
    for i in range(5):
        doc.add(GeoObject(kind="number", name=f"N_{i}", params={"value": float(i)}))

    mock_win = MockMainWindow(doc)
    inspector = RuntimeInspector(mock_win, start_time=0.0)

    # Page 1: limit 10
    page1 = inspector.list_objects(limit=10)
    assert page1["returned_count"] == 10
    assert page1["total_count"] == 20
    assert page1["truncated"] is True
    assert page1["next_cursor"] is not None

    # Page 2: with cursor
    page2 = inspector.list_objects(limit=10, cursor=page1["next_cursor"])
    assert page2["returned_count"] == 10
    assert page2["total_count"] == 20
    assert page2["truncated"] is False
    assert page2["next_cursor"] is None

    # Verify no overlap between page 1 and page 2
    ids1 = {item["id"] for item in page1["items"]}
    ids2 = {item["id"] for item in page2["items"]}
    assert ids1.isdisjoint(ids2)
    assert len(ids1) + len(ids2) == 20

    # Filter by kind
    filtered = inspector.list_objects(kind="number")
    assert filtered["returned_count"] == 5
    assert filtered["total_count"] == 5
    assert all(item["kind"] == "number" for item in filtered["items"])


def test_list_objects_revision_mismatch_and_invalid_cursor() -> None:
    doc = Document("DocRev")
    doc.add(GeoObject(kind="point", name="A", params={"x": 0.0, "y": 0.0}))
    mock_win = MockMainWindow(doc)
    inspector = RuntimeInspector(mock_win, start_time=0.0)

    # Malformed cursor
    with pytest.raises(ProtocolError) as exc_info:
        inspector.list_objects(cursor="invalid")
    assert exc_info.value.code == INVALID_PARAMS

    # Revision mismatch
    with pytest.raises(ProtocolError) as exc_info:
        inspector.list_objects(cursor="999:0")
    assert exc_info.value.code == DOCUMENT_REVISION_MISMATCH


def test_inspect_object_success() -> None:
    doc = Document("InspectDoc")
    pt_a = doc.add(GeoObject(kind="point", name="A", params={"x": 1.0, "y": 2.0}))
    pt_b = doc.add(GeoObject(kind="point", name="B", params={"x": 4.0, "y": 6.0}))
    seg = doc.add(GeoObject(kind="segment", name="s", dependencies=(pt_a.id, pt_b.id)))

    mock_win = MockMainWindow(doc)
    mock_win.selection_coordinator.selected_ids = frozenset([pt_a.id])
    inspector = RuntimeInspector(mock_win, start_time=0.0)

    # Inspect Point A (selected)
    info_a = inspector.inspect_object(pt_a.id)
    assert info_a["id"] == pt_a.id
    assert info_a["name"] == "A"
    assert info_a["kind"] == "point"
    assert info_a["selected"] is True
    assert info_a["visible"] is True
    assert info_a["validity"] == "valid"
    assert info_a["computed_geometry"] == {"type": "point", "x": 1.0, "y": 2.0}
    assert info_a["errors"] == []

    # Inspect Segment s (computed length 5.0)
    info_s = inspector.inspect_object(seg.id)
    assert info_s["id"] == seg.id
    assert info_s["kind"] == "segment"
    assert info_s["selected"] is False
    assert info_s["validity"] == "valid"
    assert info_s["computed_geometry"]["type"] == "segment"
    assert info_s["computed_geometry"]["length"] == 5.0


def test_inspect_object_not_found_and_invalid_params() -> None:
    doc = Document("Doc")
    mock_win = MockMainWindow(doc)
    inspector = RuntimeInspector(mock_win, start_time=0.0)

    # Empty object_id
    with pytest.raises(ProtocolError) as exc_info:
        inspector.inspect_object("")
    assert exc_info.value.code == INVALID_PARAMS

    # Unknown ID
    with pytest.raises(ProtocolError) as exc_info:
        inspector.inspect_object("00000000-0000-0000-0000-000000000000")
    assert exc_info.value.code == OBJECT_NOT_FOUND
    assert "not found" in str(exc_info.value)
