"""Unit tests for descriptive statistics module (PyGeoLab 1.3 Section 2)."""

import math

import pytest

from pygeolab.data.dataset import DatasetObject
from pygeolab.data.statistics import (
    compute_descriptive_stats,
    detect_outliers,
    percentile,
    quartiles,
)


def test_percentile_linear_interpolation() -> None:
    data = [10.0, 20.0, 35.0, 40.0, 50.0]
    assert percentile(data, 0.0) == 10.0
    assert percentile(data, 100.0) == 50.0
    assert percentile(data, 50.0) == 35.0
    # 25th percentile: rank = 0.25 * 4 = 1.0 -> index 1 is 20.0
    assert percentile(data, 25.0) == 20.0
    # 75th percentile: rank = 0.75 * 4 = 3.0 -> index 3 is 40.0
    assert percentile(data, 75.0) == 40.0


def test_percentile_single_value() -> None:
    assert percentile([42.0], 50.0) == 42.0
    assert percentile([42.0], 0.0) == 42.0
    assert percentile([42.0], 100.0) == 42.0


def test_percentile_validation() -> None:
    with pytest.raises(ValueError, match="vide"):
        percentile([], 50.0)
    with pytest.raises(ValueError, match="compris entre 0 et 100"):
        percentile([1.0, 2.0], -5.0)
    with pytest.raises(ValueError, match="compris entre 0 et 100"):
        percentile([1.0, 2.0], 105.0)


def test_quartiles_calculation() -> None:
    # 1 to 9
    vals = list(range(1, 10))
    q1, q2, q3 = quartiles(vals)
    assert q1 == 3.0
    assert q2 == 5.0
    assert q3 == 7.0


def test_descriptive_stats_normal_series() -> None:
    vals = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    stats = compute_descriptive_stats(vals)
    assert stats.count == 8
    assert stats.sum == 40.0
    assert stats.mean == 5.0
    assert stats.min == 2.0
    assert stats.max == 9.0
    assert stats.range == 7.0
    assert stats.median == 4.5
    # Variance pop: sum((x-5)^2)/8 = (9 + 1 + 1 + 1 + 0 + 0 + 4 + 16)/8 = 32/8 = 4.0
    assert math.isclose(stats.variance_population, 4.0)
    assert math.isclose(stats.stdev_population, 2.0)
    # Variance sample: 32 / 7 = 4.57142857...
    assert stats.variance_sample is not None
    assert math.isclose(stats.variance_sample, 32.0 / 7.0)
    assert stats.stdev_sample is not None
    assert math.isclose(stats.stdev_sample, math.sqrt(32.0 / 7.0))
    assert stats.q3 >= stats.q1
    assert stats.iqr == stats.q3 - stats.q1

    d = stats.to_dict()
    assert d["count"] == 8
    assert d["mean"] == 5.0


def test_descriptive_stats_single_element() -> None:
    stats = compute_descriptive_stats([15.0])
    assert stats.count == 1
    assert stats.sum == 15.0
    assert stats.mean == 15.0
    assert stats.median == 15.0
    assert stats.min == 15.0
    assert stats.max == 15.0
    assert stats.range == 0.0
    assert stats.variance_population == 0.0
    assert stats.stdev_population == 0.0
    assert stats.variance_sample is None
    assert stats.stdev_sample is None
    assert stats.q1 == 15.0
    assert stats.q3 == 15.0
    assert stats.iqr == 0.0
    assert stats.outliers == ()


def test_descriptive_stats_constant_series() -> None:
    stats = compute_descriptive_stats([7.0, 7.0, 7.0, 7.0, 7.0])
    assert stats.count == 5
    assert stats.mean == 7.0
    assert stats.variance_population == 0.0
    assert stats.variance_sample == 0.0
    assert stats.range == 0.0
    assert stats.iqr == 0.0
    assert stats.outliers == ()


def test_outlier_detection_tukey() -> None:
    # Most values around 10-12, one extreme outlier at 100
    vals = [10.0, 10.5, 11.0, 11.2, 11.5, 12.0, 100.0]
    outliers = detect_outliers(vals, k=1.5)
    assert 100.0 in outliers
    assert len(outliers) == 1

    # Small list (< 4 items) produces no outliers
    assert detect_outliers([1.0, 100.0]) == ()


def test_invalid_values_rejection() -> None:
    with pytest.raises(ValueError, match="vide"):
        compute_descriptive_stats([])

    with pytest.raises(ValueError, match="non finie"):
        compute_descriptive_stats([1.0, float("nan"), 3.0])

    with pytest.raises(ValueError, match="non finie"):
        compute_descriptive_stats([1.0, float("inf"), 3.0])

    with pytest.raises(ValueError, match="non numérique"):
        compute_descriptive_stats([1.0, "abc", 3.0])  # type: ignore


def test_dataset_object_descriptive_stats_method() -> None:
    ds = DatasetObject.from_xy(
        x=[1.0, 2.0, 3.0, 4.0, 5.0],
        y=[10.0, 20.0, 30.0, 40.0, 50.0],
        name="TestDS",
    )
    stat_x = ds.descriptive_stats("x")
    assert stat_x.mean == 3.0
    assert stat_x.min == 1.0
    assert stat_x.max == 5.0

    stat_y = ds.descriptive_stats(1)
    assert stat_y.mean == 30.0
    assert stat_y.min == 10.0
    assert stat_y.max == 50.0
