"""Comprehensive tests for PyGeoLab geometry object inspector and serialization."""

from __future__ import annotations

from typing import Any
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
        "sample_points": [],
        "total_points": 0,
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

    # 1. Malformed cursor (not base64, random string)
    with pytest.raises(ProtocolError) as exc_info:
        inspector.list_objects(cursor="invalid")
    assert exc_info.value.code == INVALID_PARAMS

    # 2. Oversized cursor (> 256 chars)
    with pytest.raises(ProtocolError) as exc_info:
        inspector.list_objects(cursor="x" * 257)
    assert exc_info.value.code == INVALID_PARAMS

    # 3. Forged base64 cursor but not JSON
    import base64

    not_json_b64 = base64.urlsafe_b64encode(b"not json").decode("ascii")
    with pytest.raises(ProtocolError) as exc_info:
        inspector.list_objects(cursor=not_json_b64)
    assert exc_info.value.code == INVALID_PARAMS

    # 4. Forged JSON cursor with invalid offset (negative)
    import json

    bad_payload = {"v": 1, "dn": "DocRev", "dp": id(doc), "sig": "abc", "k": None, "off": -1}
    bad_offset_b64 = base64.urlsafe_b64encode(json.dumps(bad_payload).encode()).decode("ascii")
    with pytest.raises(ProtocolError) as exc_info:
        inspector.list_objects(cursor=bad_offset_b64)
    assert exc_info.value.code == INVALID_PARAMS

    # 5. Filter mismatch: cursor created with kind='point', used with kind='circle'
    inspector.list_objects(limit=1, kind="point")
    # Add a second point to have next_cursor
    doc.add(GeoObject(kind="point", name="B", params={"x": 1.0, "y": 1.0}))
    page1 = inspector.list_objects(limit=1, kind="point")
    assert page1["next_cursor"] is not None
    with pytest.raises(ProtocolError) as exc_info:
        inspector.list_objects(cursor=page1["next_cursor"], kind="circle")
    assert exc_info.value.code == INVALID_PARAMS
    assert "mismatch" in str(exc_info.value)

    # 6. Document mutation during pagination: add an object between pages
    cur = page1["next_cursor"]
    doc.add(GeoObject(kind="point", name="C", params={"x": 2.0, "y": 2.0}))
    with pytest.raises(ProtocolError) as exc_info:
        inspector.list_objects(cursor=cur, kind="point")
    assert exc_info.value.code == DOCUMENT_REVISION_MISMATCH
    assert exc_info.value.data is not None

    # 7. Document instance changed
    doc2 = Document("DifferentDoc")
    doc2.add(GeoObject(kind="point", name="D", params={"x": 0.0, "y": 0.0}))
    mock_win2 = MockMainWindow(doc2)
    inspector2 = RuntimeInspector(mock_win2, start_time=0.0)
    with pytest.raises(ProtocolError) as exc_info:
        inspector2.list_objects(cursor=cur, kind="point")
    assert exc_info.value.code == DOCUMENT_REVISION_MISMATCH


def test_pagination_large_dataset_over_100_objects() -> None:
    """Test pagination of 150 objects across multiple pages with canonical order."""
    doc = Document("BigDoc")
    for i in range(150):
        doc.add(GeoObject(kind="point", name=f"P_{i:03d}", params={"x": float(i), "y": float(i)}))

    mock_win = MockMainWindow(doc)
    inspector = RuntimeInspector(mock_win, start_time=0.0)

    # Page 1: limit 60
    p1 = inspector.list_objects(limit=60)
    assert p1["returned_count"] == 60
    assert p1["total_count"] == 150
    assert p1["truncated"] is True
    assert p1["next_cursor"] is not None

    # Page 2: limit 60
    p2 = inspector.list_objects(limit=60, cursor=p1["next_cursor"])
    assert p2["returned_count"] == 60
    assert p2["total_count"] == 150
    assert p2["truncated"] is True
    assert p2["next_cursor"] is not None

    # Page 3: limit 60 (remaining 30)
    p3 = inspector.list_objects(limit=60, cursor=p2["next_cursor"])
    assert p3["returned_count"] == 30
    assert p3["total_count"] == 150
    assert p3["truncated"] is False
    assert p3["next_cursor"] is None

    # Verify canonical deterministic ordering (sorted by ID)
    ids_p1 = [item["id"] for item in p1["items"]]
    ids_p2 = [item["id"] for item in p2["items"]]
    ids_p3 = [item["id"] for item in p3["items"]]
    all_ids = ids_p1 + ids_p2 + ids_p3
    assert len(all_ids) == 150
    assert len(set(all_ids)) == 150
    assert all_ids == sorted(doc.objects.keys())


def test_strict_parameter_validation() -> None:
    doc = Document("DocValid")
    mock_win = MockMainWindow(doc)
    inspector = RuntimeInspector(mock_win, start_time=0.0)

    # limit validation (reject bool, <=0, >100, str)
    for bad_limit in (True, False, 0, -5, 101, "50"):
        with pytest.raises(ProtocolError) as exc_info:
            inspector.list_objects(limit=bad_limit)  # type: ignore[arg-type]
        assert exc_info.value.code == INVALID_PARAMS

    # kind validation (reject bool, unknown kind, empty, too long)
    for bad_kind in (True, "not_a_kind", "", "x" * 100):
        with pytest.raises(ProtocolError) as exc_info:
            inspector.list_objects(kind=bad_kind)  # type: ignore[arg-type]
        assert exc_info.value.code == INVALID_PARAMS

    # object_id validation (reject bool, empty, > 128 chars, int)
    for bad_id in (True, "", "x" * 200, 123):
        with pytest.raises(ProtocolError) as exc_info:
            inspector.inspect_object(bad_id)  # type: ignore[arg-type]
        assert exc_info.value.code == INVALID_PARAMS


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

    # Unknown ID
    with pytest.raises(ProtocolError) as exc_info:
        inspector.inspect_object("00000000-0000-0000-0000-000000000000")
    assert exc_info.value.code == OBJECT_NOT_FOUND
    assert "not found" in str(exc_info.value)


def test_serialization_bounding_and_cycle_detection() -> None:
    """Test bounds on recursion, collections, strings, and cycles."""
    # Cyclic dict
    d: dict[str, Any] = {"a": 1}
    d["self"] = d
    warnings: list[str] = []
    sanitized = _sanitize_json_value(d, warnings=warnings)
    assert sanitized["a"] == 1
    assert sanitized["self"]["_cyclic_ref"] is True
    assert any("Cyclic" in w for w in warnings)

    # Deeply nested list (> 5 levels)
    deep: list[Any] = [1]
    for _ in range(8):
        deep = [deep]
    deep_warnings: list[str] = []
    _sanitize_json_value(deep, warnings=deep_warnings)
    assert any("depth" in w for w in deep_warnings)

    # Large collection (> 100 items)
    large_list = list(range(150))
    list_warnings: list[str] = []
    sanitized_list = _sanitize_json_value(large_list, warnings=list_warnings)
    assert len(sanitized_list) == 101  # 100 items + 1 truncation marker
    assert sanitized_list[-1]["_truncated"] is True
    assert sanitized_list[-1]["total_elements"] == 150

    # Large dict (> 50 keys)
    large_dict = {f"k_{i}": i for i in range(70)}
    dict_warnings: list[str] = []
    sanitized_dict = _sanitize_json_value(large_dict, warnings=dict_warnings)
    assert sanitized_dict["_truncated"] is True
    assert sanitized_dict["_total_keys"] == 70

    # Long string (> 1000 chars)
    long_str = "a" * 1500
    str_warnings: list[str] = []
    sanitized_str = _sanitize_json_value(long_str, warnings=str_warnings)
    assert len(sanitized_str) < 1100
    assert "[truncated]" in sanitized_str

    # Unsupported python object
    class CustomObj:
        pass

    obj_warnings: list[str] = []
    sanitized_obj = _sanitize_json_value(CustomObj(), warnings=obj_warnings)
    assert sanitized_obj == {"_unserializable": True, "type": "CustomObj"}


def test_polygon_and_locus_truncation() -> None:
    # Polygon with 120 vertices
    pts = [Point2D(float(i), float(i)) for i in range(120)]
    poly = Polygon2D(tuple(pts))
    geo, errs = _serialize_geometry(poly)
    assert geo is not None
    assert geo["type"] == "polygon"
    assert geo["vertex_count"] == 120
    assert len(geo["vertices"]) == 100
    assert geo["_truncated"] is True

    # Locus with 150 points across segments
    locus_pts = tuple(Point2D(float(i), 0.0) for i in range(150))
    locus = Locus2D((locus_pts,), "tgt", "drv", 0.0, 1.0, samples=150)
    geo_loc, errs_loc = _serialize_geometry(locus)
    assert geo_loc is not None
    assert geo_loc["type"] == "locus"
    assert geo_loc["total_points"] == 150
    assert len(geo_loc["sample_points"]) == 100
    assert geo_loc["_truncated"] is True


def test_nan_infinity_handling_and_json_compliance() -> None:
    import json

    # Point with NaN
    pt_nan = Point2D(0.0, 2.0)
    object.__setattr__(pt_nan, "x", float("nan"))
    geo_nan, errs_nan = _serialize_geometry(pt_nan)
    assert geo_nan == {"type": "point", "x": None, "y": 2.0}
    assert any("non-finite" in e.lower() for e in errs_nan)

    # Segment with Inf
    pt_inf = Point2D(0.0, 1.0)
    object.__setattr__(pt_inf, "x", float("inf"))
    seg_inf = Segment2D(Point2D(0.0, 0.0), pt_inf)
    geo_inf, errs_inf = _serialize_geometry(seg_inf)
    assert geo_inf is not None
    assert geo_inf["end"]["x"] is None
    assert any("non-finite" in e.lower() for e in errs_inf)

    # Ensure valid JSON output (no NaN tokens)
    serialized = json.dumps(geo_nan)
    assert "NaN" not in serialized
    assert "null" in serialized


def test_inspection_never_mutates_document() -> None:
    """Verify strictly that reading objects does NOT mutate Document state."""
    doc = Document("ImmutableTest")
    pt1 = doc.add(GeoObject(kind="point", name="P1", params={"x": 1.0, "y": 1.0}))
    pt2 = doc.add(GeoObject(kind="point", name="P2", params={"x": 2.0, "y": 2.0}))
    doc.add(GeoObject(kind="segment", name="S1", dependencies=(pt1.id, pt2.id)))

    initial_rev = doc.revision
    initial_count = len(doc.objects)
    initial_keys = set(doc.objects.keys())

    mock_win = MockMainWindow(doc)
    inspector = RuntimeInspector(mock_win, start_time=0.0)

    # Run inspection 50 times
    for _ in range(50):
        inspector.list_objects(limit=10)
        inspector.inspect_object(pt1.id)
        inspector.inspect_object(pt2.id)

    assert doc.revision == initial_rev
    assert len(doc.objects) == initial_count
    assert set(doc.objects.keys()) == initial_keys
