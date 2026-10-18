"""Unit tests for bivariate statistics, correlation, and linear regression.

PyGeoLab 1.3 Section 3.
"""

import math

import pytest

from pygeolab.data.bivariate import (
    LinearRegressionResult,
    covariance,
    linear_regression,
    pearson_correlation,
)
from pygeolab.data.dataset import DatasetObject


def test_covariance_calculation() -> None:
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [2.0, 4.0, 6.0, 8.0, 10.0]
    # Sample covariance: cov(x, 2x) = 2 * var(x) = 2 * 2.5 = 5.0
    cov_sample = covariance(x, y, sample=True)
    assert math.isclose(cov_sample, 5.0)

    # Population covariance: 5.0 * 4 / 5 = 4.0
    cov_pop = covariance(x, y, sample=False)
    assert math.isclose(cov_pop, 4.0)


def test_pearson_correlation_perfect() -> None:
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y_pos = [10.0, 20.0, 30.0, 40.0, 50.0]
    y_neg = [50.0, 40.0, 30.0, 20.0, 10.0]

    assert math.isclose(pearson_correlation(x, y_pos), 1.0)
    assert math.isclose(pearson_correlation(x, y_neg), -1.0)


def test_pearson_correlation_general() -> None:
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [1.0, 3.0, 2.0, 5.0, 4.0]
    r = pearson_correlation(x, y)
    assert math.isclose(r, 0.8)


def test_linear_regression_fit_and_prediction() -> None:
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    # y = 2.5 * x + 1.2
    y = [2.5 * xi + 1.2 for xi in x]
    res: LinearRegressionResult = linear_regression(x, y)

    assert math.isclose(res.slope, 2.5)
    assert math.isclose(res.intercept, 1.2)
    assert math.isclose(res.r, 1.0)
    assert math.isclose(res.r_squared, 1.0)
    assert res.count == 5
    for residual in res.residuals:
        assert math.isclose(residual, 0.0, abs_tol=1e-12)

    # Prediction
    pred = res.predict(10.0)
    assert math.isclose(pred, 2.5 * 10.0 + 1.2)

    # Dict representation
    d = res.to_dict()
    assert d["slope"] == res.slope
    assert d["count"] == 5


def test_linear_regression_horizontal_line() -> None:
    x = [1.0, 2.0, 3.0, 4.0]
    y = [5.0, 5.0, 5.0, 5.0]
    res = linear_regression(x, y)
    assert math.isclose(res.slope, 0.0, abs_tol=1e-12)
    assert math.isclose(res.intercept, 5.0)
    assert math.isclose(res.r_squared, 1.0)


def test_validation_errors() -> None:
    # Unequal lengths
    with pytest.raises(ValueError, match="même longueur"):
        covariance([1.0, 2.0], [1.0])

    with pytest.raises(ValueError, match="même longueur"):
        pearson_correlation([1.0, 2.0], [1.0, 2.0, 3.0])

    with pytest.raises(ValueError, match="même longueur"):
        linear_regression([1.0], [1.0, 2.0])

    # Empty series
    with pytest.raises(ValueError, match="vides"):
        covariance([], [])

    # Series < 2 points
    with pytest.raises(ValueError, match="au moins 2"):
        covariance([1.0], [2.0], sample=True)

    with pytest.raises(ValueError, match="au moins 2"):
        pearson_correlation([1.0], [2.0])

    with pytest.raises(ValueError, match="au moins 2"):
        linear_regression([1.0], [2.0])

    # Constant X (zero variance)
    with pytest.raises(ValueError, match="constante"):
        linear_regression([3.0, 3.0, 3.0], [1.0, 2.0, 3.0])

    with pytest.raises(ValueError, match="variance nulle"):
        pearson_correlation([3.0, 3.0, 3.0], [1.0, 2.0, 3.0])

    # Prediction validation
    res = linear_regression([1.0, 2.0], [3.0, 4.0])
    with pytest.raises(ValueError, match="fini"):
        res.predict(float("nan"))


def test_dataset_object_bivariate_methods() -> None:
    ds = DatasetObject.from_xy(
        x=[0.0, 1.0, 2.0, 3.0, 4.0],
        y=[1.0, 3.0, 5.0, 7.0, 9.0],
        name="TestBivariate",
    )
    cov = ds.covariance(0, 1)
    assert math.isclose(cov, 5.0)

    corr = ds.correlation(0, 1)
    assert math.isclose(corr, 1.0)

    reg = ds.linear_regression(0, 1)
    assert math.isclose(reg.slope, 2.0)
    assert math.isclose(reg.intercept, 1.0)
    assert math.isclose(reg.r_squared, 1.0)
