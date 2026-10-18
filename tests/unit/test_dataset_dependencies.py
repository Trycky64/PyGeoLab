"""Unit tests for dataset integration with the dependency graph (PyGeoLab 1.3 Section 7).

Verifies:
- Linking datasets to canvas points, polygons, locus, sliders and functions.
- Points and regression lines depending on datasets.
- Fine-grained incremental cache invalidation and recomputation.
- Cycle prevention.
"""

from __future__ import annotations

import math

import pytest

from pygeolab.data.dataset import DatasetObject
from pygeolab.geometry.primitives import Line2D, Point2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject


def test_dataset_from_points_dynamic_recomputation() -> None:
    doc = Document()
    p1 = doc.add(GeoObject(name="A", kind="point", params={"x": 1.0, "y": 2.0}))
    p2 = doc.add(GeoObject(name="B", kind="point", params={"x": 3.0, "y": 4.0}))
    p3 = doc.add(GeoObject(name="C", kind="point", params={"x": 5.0, "y": 6.0}))

    # Dataset depending on points A, B, C
    ds_obj = doc.add(
        GeoObject(
            name="DataPoints",
            kind="dataset",
            dependencies=(p1.id, p2.id, p3.id),
            params={"headers": ["x", "y"], "plot_kind": "scatter"},
        )
    )

    geom = doc.get(ds_obj.id).geometry
    assert isinstance(geom, DatasetObject)
    assert geom.rows == ((1.0, 2.0), (3.0, 4.0), (5.0, 6.0))
    assert geom.descriptive_stats(0).mean == 3.0

    # Move point A
    doc.move_point(p1.id, Point2D(7.0, 8.0))
    updated_geom = doc.get(ds_obj.id).geometry
    assert isinstance(updated_geom, DatasetObject)
    assert updated_geom.rows == ((7.0, 8.0), (3.0, 4.0), (5.0, 6.0))
    assert math.isclose(updated_geom.descriptive_stats(0).mean, 5.0)


def test_dataset_from_sliders() -> None:
    doc = Document()
    s1 = doc.add(GeoObject(name="s1", kind="number", params={"value": 10.0}))
    s2 = doc.add(GeoObject(name="s2", kind="number", params={"value": 20.0}))
    s3 = doc.add(GeoObject(name="s3", kind="number", params={"value": 30.0}))

    ds_obj = doc.add(
        GeoObject(
            name="SliderSeries",
            kind="dataset",
            dependencies=(s1.id, s2.id, s3.id),
            params={"mode": "series"},
        )
    )

    geom = doc.get(ds_obj.id).geometry
    assert isinstance(geom, DatasetObject)
    assert geom.rows == ((10.0,), (20.0,), (30.0,))

    # Update slider s2
    doc.update(s2.id, params={"value": 50.0})
    updated_geom = doc.get(ds_obj.id).geometry
    assert isinstance(updated_geom, DatasetObject)
    assert updated_geom.rows == ((10.0,), (50.0,), (30.0,))


def test_point_from_dataset_mean_and_row() -> None:
    doc = Document()
    p1 = doc.add(GeoObject(name="P1", kind="point", params={"x": 0.0, "y": 0.0}))
    p2 = doc.add(GeoObject(name="P2", kind="point", params={"x": 4.0, "y": 6.0}))

    ds = doc.add(
        GeoObject(
            name="DS",
            kind="dataset",
            dependencies=(p1.id, p2.id),
        )
    )

    # Point G = mean point (centroid) of DS
    g_pt = doc.add(
        GeoObject(
            name="G",
            kind="point",
            dependencies=(ds.id,),
            params={"mode": "mean"},
        )
    )

    # Point R1 = row 1 of DS
    r1_pt = doc.add(
        GeoObject(
            name="R1",
            kind="point",
            dependencies=(ds.id,),
            params={"mode": "row", "index": 1},
        )
    )

    g_geom = doc.get(g_pt.id).geometry
    assert isinstance(g_geom, Point2D)
    assert g_geom.x == 2.0 and g_geom.y == 3.0

    r1_geom = doc.get(r1_pt.id).geometry
    assert isinstance(r1_geom, Point2D)
    assert r1_geom.x == 4.0 and r1_geom.y == 6.0

    # Move P2
    doc.move_point(p2.id, Point2D(8.0, 10.0))

    g_geom_after = doc.get(g_pt.id).geometry
    assert isinstance(g_geom_after, Point2D)
    assert g_geom_after.x == 4.0 and g_geom_after.y == 5.0

    r1_geom_after = doc.get(r1_pt.id).geometry
    assert isinstance(r1_geom_after, Point2D)
    assert r1_geom_after.x == 8.0 and r1_geom_after.y == 10.0


def test_line_from_dataset_regression() -> None:
    doc = Document()
    # y = 2 * x + 1
    p1 = doc.add(GeoObject(name="A", kind="point", params={"x": 0.0, "y": 1.0}))
    p2 = doc.add(GeoObject(name="B", kind="point", params={"x": 1.0, "y": 3.0}))
    p3 = doc.add(GeoObject(name="C", kind="point", params={"x": 2.0, "y": 5.0}))

    ds = doc.add(
        GeoObject(
            name="DS",
            kind="dataset",
            dependencies=(p1.id, p2.id, p3.id),
        )
    )

    reg_line = doc.add(
        GeoObject(
            name="RegLine",
            kind="line",
            dependencies=(ds.id,),
        )
    )

    line_geom = doc.get(reg_line.id).geometry
    assert isinstance(line_geom, Line2D)
    # y = 2*x + 1 -> passes through (0, 1) and (1, 3) and (5, 11)
    assert math.isclose(line_geom.distance(Point2D(0.0, 1.0)), 0.0, abs_tol=1e-7)
    assert math.isclose(line_geom.distance(Point2D(5.0, 11.0)), 0.0, abs_tol=1e-7)

    # Move p2
    doc.move_point(p2.id, Point2D(1.0, 3.0))


def test_dataset_from_function_sampling() -> None:
    doc = Document()
    fn = doc.add(
        GeoObject(
            name="f",
            kind="function",
            params={"source": "x^2", "variable": "x"},
        )
    )

    ds = doc.add(
        GeoObject(
            name="SampledFn",
            kind="dataset",
            dependencies=(fn.id,),
            params={"start": 0.0, "end": 4.0, "count": 5},
        )
    )

    geom = doc.get(ds.id).geometry
    assert isinstance(geom, DatasetObject)
    assert geom.row_count == 5
    assert geom.rows[0] == (0.0, 0.0)
    assert geom.rows[2] == (2.0, 4.0)
    assert geom.rows[4] == (4.0, 16.0)


def test_cycle_detection_prevents_loop() -> None:
    doc = Document()
    p1 = doc.add(GeoObject(name="P1", kind="point", params={"x": 0.0, "y": 0.0}))
    ds = doc.add(
        GeoObject(
            name="DS",
            kind="dataset",
            dependencies=(p1.id,),
        )
    )

    # Trying to make P1 depend on DS creates a cycle P1 -> DS -> P1
    with pytest.raises(ValueError, match="cyclique"):
        doc.update(p1.id, dependencies=(ds.id,))


def test_fine_cache_invalidation() -> None:
    doc = Document()
    p1 = doc.add(GeoObject(name="A", kind="point", params={"x": 1.0, "y": 2.0}))
    p2 = doc.add(GeoObject(name="B", kind="point", params={"x": 3.0, "y": 4.0}))
    unrelated_p = doc.add(GeoObject(name="C", kind="point", params={"x": 10.0, "y": 10.0}))

    ds = doc.add(GeoObject(name="DS", kind="dataset", dependencies=(p1.id, p2.id)))
    g = doc.add(GeoObject(name="G", kind="point", dependencies=(ds.id,), params={"mode": "mean"}))

    # Move p1
    doc.move_point(p1.id, Point2D(5.0, 6.0))

    # Recomputed must contain p1, ds, g, but NOT unrelated_p
    assert p1.id in doc.last_recomputed
    assert ds.id in doc.last_recomputed
    assert g.id in doc.last_recomputed
    assert unrelated_p.id not in doc.last_recomputed


def test_dataset_from_polygon() -> None:
    doc = Document()
    p1 = doc.add(GeoObject(name="A", kind="point", params={"x": 0.0, "y": 0.0}))
    p2 = doc.add(GeoObject(name="B", kind="point", params={"x": 2.0, "y": 0.0}))
    p3 = doc.add(GeoObject(name="C", kind="point", params={"x": 1.0, "y": 2.0}))
    poly = doc.add(
        GeoObject(
            name="Tri",
            kind="polygon",
            dependencies=(p1.id, p2.id, p3.id),
        )
    )

    ds = doc.add(
        GeoObject(
            name="PolyData",
            kind="dataset",
            dependencies=(poly.id,),
        )
    )

    geom = doc.get(ds.id).geometry
    assert isinstance(geom, DatasetObject)
    assert geom.row_count == 3
    assert geom.rows == ((0.0, 0.0), (2.0, 0.0), (1.0, 2.0))


def test_dataset_from_locus() -> None:
    doc = Document()
    driver = doc.add(GeoObject(name="t", kind="number", params={"value": 0.0}))
    # Target point: P(t, 2*t)
    target = doc.add(
        GeoObject(
            name="P",
            kind="point",
            dependencies=(driver.id,),
            params={"x": 0.0, "y": 0.0},
        )
    )
    # Locus tracing P when driver t sweeps from 0 to 1
    locus = doc.add(
        GeoObject(
            name="Loc",
            kind="locus",
            dependencies=(target.id, driver.id),
            params={"start": 0.0, "end": 1.0, "samples": 5},
        )
    )

    ds = doc.add(
        GeoObject(
            name="LocusData",
            kind="dataset",
            dependencies=(locus.id,),
        )
    )

    geom = doc.get(ds.id).geometry
    assert isinstance(geom, DatasetObject)
    assert geom.plot_kind == "scatter"
