"""Advanced regression curves and curve fitting algorithms for PyGeoLab datasets.

Provides clean, pure, deterministic implementations using standard Python:
- Polynomial regression (degree 1 to 5) solved via Normal Equations with Gaussian Elimination.
- Exponential regression (y = a * exp(b * x)) fitted via linearization (ln(y) = ln(a) + b * x).
- Logarithmic regression (y = a + b * ln(x)) fitted via linearization on ln(x).
- Power regression (y = a * x^b) fitted via linearization (ln(y) = ln(a) + b * ln(x)).
- Calculation of R^2 and residuals.
- Generation of algebraic expressions and FunctionObject instances.
- Comprehensive domain and singularity validations.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pygeolab.data.statistics import _validate_numeric_values

if TYPE_CHECKING:
    from pygeolab.math_engine.functions import FunctionObject


@dataclass(frozen=True)
class FitResult:
    """Immutable result container for curve fitting."""

    model_kind: str  # "polynomial", "exponential", "logarithmic", "power"
    parameters: tuple[float, ...]  # e.g. (c0, c1, c2, ...) for c0 + c1*x + c2*x^2
    expression: str
    r_squared: float
    residuals: tuple[float, ...]
    count: int

    def predict(self, x: float) -> float:
        """Evaluate the fitted model at a specific x coordinate."""
        if not isinstance(x, (int, float)) or not math.isfinite(float(x)):
            raise ValueError(f"Abscisse non finie invalide pour prédiction : {x!r}")
        x_val = float(x)

        if self.model_kind == "polynomial":
            return sum(coef * (x_val**i) for i, coef in enumerate(self.parameters))

        if self.model_kind == "exponential":
            a, b = self.parameters
            return a * math.exp(b * x_val)

        if self.model_kind == "logarithmic":
            a, b = self.parameters
            if x_val <= 0.0:
                raise ValueError(
                    f"x doit être strictement positif pour un modèle logarithmique : {x_val}"
                )
            return a + b * math.log(x_val)

        if self.model_kind == "power":
            a, b = self.parameters
            if x_val <= 0.0:
                raise ValueError(
                    f"x doit être strictement positif pour un modèle puissance : {x_val}"
                )
            return float(a * (x_val**b))

        raise ValueError(f"Modèle d'ajustement non reconnu : {self.model_kind}")

    def to_function(self, name: str = "f") -> FunctionObject:
        """Create a FunctionObject from the fitted mathematical model expression."""
        from pygeolab.math_engine.functions import FunctionObject

        return FunctionObject.from_source(name=name, variable="x", source=self.expression)

    def to_dict(self) -> dict[str, float | int | str | tuple[float, ...]]:
        """Serialize fitting result."""
        return {
            "model_kind": self.model_kind,
            "parameters": self.parameters,
            "expression": self.expression,
            "r_squared": self.r_squared,
            "residuals": self.residuals,
            "count": self.count,
        }


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve A * x = b using Gaussian elimination with partial pivoting."""
    n = len(vector)
    a = [row[:] for row in matrix]
    b = list(vector)

    for i in range(n):
        # Find pivot
        max_row = i
        max_val = abs(a[i][i])
        for k in range(i + 1, n):
            if abs(a[k][i]) > max_val:
                max_val = abs(a[k][i])
                max_row = k

        if max_val < 1e-12:
            raise ValueError("Système linéaire singulier ou mal conditionné lors de l'ajustement.")

        a[i], a[max_row] = a[max_row], a[i]
        b[i], b[max_row] = b[max_row], b[i]

        for k in range(i + 1, n):
            factor = a[k][i] / a[i][i]
            b[k] -= factor * b[i]
            for j in range(i, n):
                a[k][j] -= factor * a[i][j]

    # Back substitution
    solution = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = sum(a[i][j] * solution[j] for j in range(i + 1, n))
        solution[i] = (b[i] - s) / a[i][i]

    return solution


def fit_polynomial(x: Sequence[float], y: Sequence[float], degree: int = 2) -> FitResult:
    """Fit a polynomial of given degree: y = c0 + c1*x + c2*x^2 + ... + c_deg*x^deg."""
    if not (1 <= degree <= 5):
        raise ValueError(f"Le degré polynomial doit être compris entre 1 et 5, reçu : {degree}")

    clean_x = _validate_numeric_values(x)
    clean_y = _validate_numeric_values(y)
    n = len(clean_x)
    if n != len(clean_y):
        raise ValueError(f"Séries de longueurs inégales ({n} != {len(clean_y)})")
    if n <= degree:
        raise ValueError(
            f"L'ajustement polynomial de degré {degree} requiert au moins {degree + 1} points."
        )

    m = degree + 1
    # Build Normal equations: X^T * X * c = X^T * y
    # A_jk = sum(x_i ^ (j + k))
    # B_j = sum(y_i * x_i ^ j)
    matrix = [[0.0] * m for _ in range(m)]
    vector = [0.0] * m

    for xi, yi in zip(clean_x, clean_y, strict=True):
        powers = [xi**p for p in range(2 * degree + 1)]
        for j in range(m):
            vector[j] += yi * powers[j]
            for k in range(m):
                matrix[j][k] += powers[j + k]

    coeffs = _solve_linear_system(matrix, vector)

    # Compute predictions, residuals, and R^2
    mean_y = sum(clean_y) / n
    ss_tot = sum((yi - mean_y) ** 2 for yi in clean_y)
    predictions = [sum(c * (xi**p) for p, c in enumerate(coeffs)) for xi in clean_x]
    residuals = tuple(yi - y_pred for yi, y_pred in zip(clean_y, predictions, strict=True))
    ss_res = sum(r**2 for r in residuals)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-12 else 1.0
    r_squared = max(0.0, min(1.0, r_squared))

    # Format algebraic expression
    terms: list[str] = []
    for p, c in enumerate(coeffs):
        if abs(c) < 1e-12 and len(coeffs) > 1:
            continue
        c_str = f"{c:.6g}"
        if p == 0:
            terms.append(c_str)
        elif p == 1:
            terms.append(f"{c_str}*x")
        else:
            terms.append(f"{c_str}*x^{p}")
    expression = " + ".join(terms).replace("+ -", "- ") if terms else "0"

    return FitResult(
        model_kind="polynomial",
        parameters=tuple(coeffs),
        expression=expression,
        r_squared=r_squared,
        residuals=residuals,
        count=n,
    )


def fit_exponential(x: Sequence[float], y: Sequence[float]) -> FitResult:
    """Fit an exponential model: y = a * exp(b * x). Requires y > 0 for all points."""
    clean_x = _validate_numeric_values(x)
    clean_y = _validate_numeric_values(y)
    n = len(clean_x)
    if n != len(clean_y):
        raise ValueError("Séries de longueurs inégales")
    if n < 2:
        raise ValueError("L'ajustement exponentiel requiert au moins 2 points.")
    if any(yi <= 0.0 for yi in clean_y):
        raise ValueError(
            "L'ajustement exponentiel requiert des ordonnées strictement positives (y > 0)."
        )

    # Linearize: ln(y) = ln(a) + b * x
    ln_y = [math.log(yi) for yi in clean_y]
    mean_x = sum(clean_x) / n
    mean_ln_y = sum(ln_y) / n

    diff_x = [xi - mean_x for xi in clean_x]
    diff_ln_y = [ly - mean_ln_y for ly in ln_y]

    sum_sq_x = sum(dx**2 for dx in diff_x)
    if sum_sq_x <= 0.0:
        raise ValueError("Ajustement impossible : la variable X est constante.")

    sum_cross = sum(dx * dy for dx, dy in zip(diff_x, diff_ln_y, strict=True))
    b = sum_cross / sum_sq_x
    ln_a = mean_ln_y - b * mean_x
    a = math.exp(ln_a)

    # Predictions in original scale
    mean_y = sum(clean_y) / n
    ss_tot = sum((yi - mean_y) ** 2 for yi in clean_y)
    predictions = [a * math.exp(b * xi) for xi in clean_x]
    residuals = tuple(yi - y_pred for yi, y_pred in zip(clean_y, predictions, strict=True))
    ss_res = sum(r**2 for r in residuals)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-12 else 1.0
    r_squared = max(0.0, min(1.0, r_squared))

    expression = f"{a:.6g} * exp({b:.6g} * x)"

    return FitResult(
        model_kind="exponential",
        parameters=(a, b),
        expression=expression,
        r_squared=r_squared,
        residuals=residuals,
        count=n,
    )


def fit_logarithmic(x: Sequence[float], y: Sequence[float]) -> FitResult:
    """Fit a logarithmic model: y = a + b * ln(x). Requires x > 0 for all points."""
    clean_x = _validate_numeric_values(x)
    clean_y = _validate_numeric_values(y)
    n = len(clean_x)
    if n != len(clean_y):
        raise ValueError("Séries de longueurs inégales")
    if n < 2:
        raise ValueError("L'ajustement logarithmique requiert au moins 2 points.")
    if any(xi <= 0.0 for xi in clean_x):
        raise ValueError(
            "L'ajustement logarithmique requiert des abscisses strictement positives (x > 0)."
        )

    # Linearize: y = a + b * ln(x)
    ln_x = [math.log(xi) for xi in clean_x]
    mean_ln_x = sum(ln_x) / n
    mean_y = sum(clean_y) / n

    diff_ln_x = [lx - mean_ln_x for lx in ln_x]
    diff_y = [yi - mean_y for yi in clean_y]

    sum_sq_ln_x = sum(dx**2 for dx in diff_ln_x)
    if sum_sq_ln_x <= 0.0:
        raise ValueError("Ajustement impossible : la variable X est constante.")

    sum_cross = sum(dx * dy for dx, dy in zip(diff_ln_x, diff_y, strict=True))
    b = sum_cross / sum_sq_ln_x
    a = mean_y - b * mean_ln_x

    # Predictions
    ss_tot = sum((yi - mean_y) ** 2 for yi in clean_y)
    predictions = [a + b * math.log(xi) for xi in clean_x]
    residuals = tuple(yi - y_pred for yi, y_pred in zip(clean_y, predictions, strict=True))
    ss_res = sum(r**2 for r in residuals)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-12 else 1.0
    r_squared = max(0.0, min(1.0, r_squared))

    sign = "+" if b >= 0 else "-"
    expression = f"{a:.6g} {sign} {abs(b):.6g} * ln(x)"

    return FitResult(
        model_kind="logarithmic",
        parameters=(a, b),
        expression=expression,
        r_squared=r_squared,
        residuals=residuals,
        count=n,
    )
