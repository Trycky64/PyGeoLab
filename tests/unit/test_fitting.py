"""Unit tests for regression and curve fitting algorithms (PyGeoLab 1.3 Section 6)."""

import math

import pytest

from pygeolab.data.dataset import DatasetObject
from pygeolab.data.fitting import (
    FitResult,
    fit_exponential,
    fit_logarithmic,
    fit_polynomial,
)


def test_fit_polynomial_linear() -> None:
    # Degree 1: y = 3 * x + 4
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [3.0 * xi + 4.0 for xi in x]
    res: FitResult = fit_polynomial(x, y, degree=1)

    assert math.isclose(res.parameters[0], 4.0, abs_tol=1e-7)
    assert math.isclose(res.parameters[1], 3.0, abs_tol=1e-7)
    assert math.isclose(res.r_squared, 1.0)
    assert res.predict(5.0) == 3.0 * 5.0 + 4.0


def test_fit_polynomial_quadratic() -> None:
    # Degree 2: y = 2 * x^2 - 5 * x + 3
    x = [-2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
    y = [2.0 * xi**2 - 5.0 * xi + 3.0 for xi in x]
    res = fit_polynomial(x, y, degree=2)

    assert math.isclose(res.parameters[0], 3.0, abs_tol=1e-7)
    assert math.isclose(res.parameters[1], -5.0, abs_tol=1e-7)
    assert math.isclose(res.parameters[2], 2.0, abs_tol=1e-7)
    assert math.isclose(res.r_squared, 1.0)
    assert math.isclose(res.predict(4.0), 2.0 * 16 - 5.0 * 4 + 3.0)


def test_fit_exponential() -> None:
    # y = 2.0 * exp(0.5 * x)
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    y = [2.0 * math.exp(0.5 * xi) for xi in x]
    res = fit_exponential(x, y)

    assert math.isclose(res.parameters[0], 2.0, rel_tol=1e-5)
    assert math.isclose(res.parameters[1], 0.5, rel_tol=1e-5)
    assert math.isclose(res.r_squared, 1.0)
    assert math.isclose(res.predict(5.0), 2.0 * math.exp(0.5 * 5.0))


def test_fit_logarithmic() -> None:
    # y = 1.5 + 2.0 * ln(x)
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [1.5 + 2.0 * math.log(xi) for xi in x]
    res = fit_logarithmic(x, y)

    assert math.isclose(res.parameters[0], 1.5, abs_tol=1e-7)
    assert math.isclose(res.parameters[1], 2.0, abs_tol=1e-7)
    assert math.isclose(res.r_squared, 1.0)
    assert math.isclose(res.predict(10.0), 1.5 + 2.0 * math.log(10.0))


def test_fitting_validation_and_errors() -> None:
    # Invalid degree
    with pytest.raises(ValueError, match="degré polynomial"):
        fit_polynomial([1.0, 2.0], [3.0, 4.0], degree=0)

    with pytest.raises(ValueError, match="degré polynomial"):
        fit_polynomial([1.0, 2.0], [3.0, 4.0], degree=6)

    # Not enough points
    with pytest.raises(ValueError, match="au moins"):
        fit_polynomial([1.0, 2.0], [3.0, 4.0], degree=2)

    # Unequal lengths
    with pytest.raises(ValueError, match="longueurs inégales"):
        fit_polynomial([1.0, 2.0, 3.0], [1.0, 2.0], degree=1)

    # Exponential requires y > 0
    with pytest.raises(ValueError, match="strictement positives"):
        fit_exponential([1.0, 2.0], [0.0, 5.0])

    with pytest.raises(ValueError, match="strictement positives"):
        fit_exponential([1.0, 2.0], [-1.0, 5.0])

    # Logarithmic requires x > 0
    with pytest.raises(ValueError, match="strictement positives"):
        fit_logarithmic([0.0, 1.0], [1.0, 2.0])

    with pytest.raises(ValueError, match="strictement positives"):
        fit_logarithmic([-2.0, 1.0], [1.0, 2.0])

    # Prediction on invalid values
    res = fit_polynomial([1.0, 2.0, 3.0], [2.0, 4.0, 6.0], degree=1)
    with pytest.raises(ValueError, match="finie"):
        res.predict(float("nan"))


def test_dataset_fitting_methods() -> None:
    ds = DatasetObject.from_xy(
        x=[1.0, 2.0, 3.0, 4.0],
        y=[1.0, 4.0, 9.0, 16.0],
        name="Squares",
    )
    poly = ds.fit_polynomial(degree=2)
    assert math.isclose(poly.r_squared, 1.0)
    assert math.isclose(poly.predict(5.0), 25.0)

    d = poly.to_dict()
    assert d["model_kind"] == "polynomial"
    assert d["count"] == 4

    fn = poly.to_function(name="f_fit")
    assert fn.name == "f_fit"
    assert math.isclose(fn.evaluate(5.0), 25.0)
