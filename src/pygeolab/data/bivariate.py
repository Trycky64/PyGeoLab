"""Bivariate statistics, correlation, and linear regression for PyGeoLab.

Provides pure, deterministic calculations for:
- Population and sample covariance
- Pearson correlation coefficient (r)
- Ordinary Least Squares (OLS) simple linear regression (y = slope * x + intercept)
- Coefficient of determination (R^2)
- Residuals analysis
- Prediction on new x values
- Strict input validation (equal series length, finite floats, non-constant variance)
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from pygeolab.data.statistics import _validate_numeric_values


@dataclass(frozen=True)
class LinearRegressionResult:
    """Immutable result container for simple linear regression."""

    slope: float
    intercept: float
    r: float
    r_squared: float
    covariance: float
    residuals: tuple[float, ...]
    count: int

    def predict(self, x: float) -> float:
        """Predict the dependent variable y for a given independent variable x."""
        if not isinstance(x, (int, float)) or not math.isfinite(float(x)):
            raise ValueError(f"La valeur x doit être un nombre fini, reçu : {x!r}")
        return self.slope * float(x) + self.intercept

    def to_dict(self) -> dict[str, float | int | tuple[float, ...]]:
        """Convert result to dictionary representation."""
        return {
            "slope": self.slope,
            "intercept": self.intercept,
            "r": self.r,
            "r_squared": self.r_squared,
            "covariance": self.covariance,
            "residuals": self.residuals,
            "count": self.count,
        }


def _validate_paired_series(
    x: Sequence[float], y: Sequence[float]
) -> tuple[list[float], list[float]]:
    """Validate paired numeric series ensuring equal non-empty length and finite numbers."""
    clean_x = _validate_numeric_values(x)
    clean_y = _validate_numeric_values(y)

    if len(clean_x) != len(clean_y):
        raise ValueError(
            f"Les séries X et Y doivent avoir la même longueur ({len(clean_x)} != {len(clean_y)})"
        )
    if len(clean_x) == 0:
        raise ValueError("Impossible de calculer des statistiques bivariées sur des séries vides.")

    return clean_x, clean_y


def covariance(x: Sequence[float], y: Sequence[float], sample: bool = True) -> float:
    """Compute covariance between x and y.

    If sample=True (default), divides by (n - 1) (unbiased sample covariance).
    If sample=False, divides by n (population covariance).
    """
    clean_x, clean_y = _validate_paired_series(x, y)
    n = len(clean_x)
    if n < 2 and sample:
        raise ValueError("Le calcul de la covariance d'échantillon requiert au moins 2 points.")

    mean_x = sum(clean_x) / n
    mean_y = sum(clean_y) / n

    sum_cross = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(clean_x, clean_y, strict=True))
    divisor = (n - 1) if sample else n
    return sum_cross / divisor


def pearson_correlation(x: Sequence[float], y: Sequence[float]) -> float:
    """Compute Pearson correlation coefficient r between x and y.

    Returns r in [-1.0, 1.0].
    Raises ValueError if either x or y has zero variance (constant values).
    """
    clean_x, clean_y = _validate_paired_series(x, y)
    n = len(clean_x)
    if n < 2:
        raise ValueError("Le calcul de la corrélation requiert au moins 2 observations.")

    mean_x = sum(clean_x) / n
    mean_y = sum(clean_y) / n

    diff_x = [xi - mean_x for xi in clean_x]
    diff_y = [yi - mean_y for yi in clean_y]

    sum_sq_x = sum(dx**2 for dx in diff_x)
    sum_sq_y = sum(dy**2 for dy in diff_y)

    if sum_sq_x <= 0.0 or sum_sq_y <= 0.0:
        raise ValueError(
            "La corrélation de Pearson est indéfinie pour une série constante (variance nulle)."
        )

    denom = math.sqrt(sum_sq_x * sum_sq_y)
    sum_cross = sum(dx * dy for dx, dy in zip(diff_x, diff_y, strict=True))
    r = sum_cross / denom
    # Clamp to [-1.0, 1.0] to guard against slight floating-point imprecision
    return max(-1.0, min(1.0, r))


def linear_regression(x: Sequence[float], y: Sequence[float]) -> LinearRegressionResult:
    """Perform Ordinary Least Squares (OLS) linear regression y = slope * x + intercept.

    Returns LinearRegressionResult with slope, intercept, r, r_squared, covariance, residuals.
    """
    clean_x, clean_y = _validate_paired_series(x, y)
    n = len(clean_x)
    if n < 2:
        raise ValueError("La régression linéaire requiert au moins 2 observations.")

    mean_x = sum(clean_x) / n
    mean_y = sum(clean_y) / n

    diff_x = [xi - mean_x for xi in clean_x]
    diff_y = [yi - mean_y for yi in clean_y]

    sum_sq_x = sum(dx**2 for dx in diff_x)
    if sum_sq_x <= 0.0:
        raise ValueError(
            "Régression linéaire impossible : la variable indépendante X est constante."
        )

    sum_sq_y = sum(dy**2 for dy in diff_y)
    sum_cross = sum(dx * dy for dx, dy in zip(diff_x, diff_y, strict=True))

    slope = sum_cross / sum_sq_x
    intercept = mean_y - slope * mean_x

    cov_val = sum_cross / (n - 1)

    if sum_sq_y > 0.0:
        r = sum_cross / math.sqrt(sum_sq_x * sum_sq_y)
        r = max(-1.0, min(1.0, r))
        r_squared = r**2
    else:
        # All y are identical; horizontal line, slope = 0, R^2 = 1.0
        r = 0.0
        r_squared = 1.0 if abs(slope) < 1e-12 else 0.0

    residuals = tuple(
        yi - (slope * xi + intercept) for xi, yi in zip(clean_x, clean_y, strict=True)
    )

    return LinearRegressionResult(
        slope=slope,
        intercept=intercept,
        r=r,
        r_squared=r_squared,
        covariance=cov_val,
        residuals=residuals,
        count=n,
    )
