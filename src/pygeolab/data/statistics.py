"""Descriptive statistics computation for PyGeoLab datasets.

Provides clean, strictly-validated statistical functions operating on sequences of floats
or extracted dataset columns without any reliance on external unmanaged libraries.
All calculations use Python standard library math and statistics modules for
maximum numerical precision and determinism.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class DescriptiveStats:
    """Immutable result container for 1D descriptive statistics."""

    count: int
    sum: float
    mean: float
    median: float
    min: float
    max: float
    range: float
    variance_population: float
    variance_sample: float | None
    stdev_population: float
    stdev_sample: float | None
    q1: float
    q2: float
    q3: float
    iqr: float
    outliers: tuple[float, ...]

    def to_dict(self) -> dict[str, float | int | tuple[float, ...] | None]:
        """Convert statistics to dictionary."""
        return {
            "count": self.count,
            "sum": self.sum,
            "mean": self.mean,
            "median": self.median,
            "min": self.min,
            "max": self.max,
            "range": self.range,
            "variance_population": self.variance_population,
            "variance_sample": self.variance_sample,
            "stdev_population": self.stdev_population,
            "stdev_sample": self.stdev_sample,
            "q1": self.q1,
            "q2": self.q2,
            "q3": self.q3,
            "iqr": self.iqr,
            "outliers": self.outliers,
        }


def _validate_numeric_values(values: Sequence[float]) -> list[float]:
    """Validate that input sequence contains finite real numbers.

    Raises:
        ValueError: If sequence is empty or contains non-finite numbers (NaN, inf).
    """
    cleaned: list[float] = []
    for idx, v in enumerate(values):
        if not isinstance(v, (int, float)):
            raise ValueError(f"Valeur non numérique à l'index {idx}: {v!r}")
        val = float(v)
        if not math.isfinite(val):
            raise ValueError(f"Valeur non finie (NaN ou Inf) à l'index {idx}: {val}")
        cleaned.append(val)
    return cleaned


def percentile(values: Sequence[float], p: float) -> float:
    """Compute the p-th percentile (0 <= p <= 100) using linear interpolation.

    Uses the standard method (equivalent to NumPy 'linear' / Excel PERCENTILE.INC).
    """
    clean = _validate_numeric_values(values)
    if not clean:
        raise ValueError("Impossible de calculer un percentile sur une série vide.")
    if not (0.0 <= p <= 100.0):
        raise ValueError(f"Le percentile doit être compris entre 0 et 100, reçu : {p}")

    sorted_vals = sorted(clean)
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]

    # Index in [0, n - 1]
    rank = (p / 100.0) * (n - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    weight = rank - lower

    if lower == upper:
        return sorted_vals[lower]
    return sorted_vals[lower] + weight * (sorted_vals[upper] - sorted_vals[lower])


def quartiles(values: Sequence[float]) -> tuple[float, float, float]:
    """Compute (Q1, Q2/Median, Q3) for the given values."""
    q1 = percentile(values, 25.0)
    q2 = percentile(values, 50.0)
    q3 = percentile(values, 75.0)
    return (q1, q2, q3)


def detect_outliers(values: Sequence[float], k: float = 1.5) -> tuple[float, ...]:
    """Identify Tukey's fences outliers in the sequence: values < Q1 - k*IQR or > Q3 + k*IQR."""
    clean = _validate_numeric_values(values)
    if len(clean) < 4:
        return ()
    q1, _, q3 = quartiles(clean)
    iqr = q3 - q1
    lower_bound = q1 - k * iqr
    upper_bound = q3 + k * iqr
    return tuple(v for v in clean if v < lower_bound or v > upper_bound)


def compute_descriptive_stats(values: Sequence[float]) -> DescriptiveStats:
    """Compute comprehensive 1D descriptive statistics for a sequence of values.

    Raises:
        ValueError: If sequence is empty or contains non-finite numbers.
    """
    clean = _validate_numeric_values(values)
    n = len(clean)
    if n == 0:
        raise ValueError("Impossible de calculer les statistiques sur un ensemble vide.")

    total = sum(clean)
    mean_val = total / n
    sorted_vals = sorted(clean)
    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]
    val_range = max_val - min_val

    # Population variance
    sum_sq_diff = sum((x - mean_val) ** 2 for x in clean)
    var_pop = sum_sq_diff / n
    stdev_pop = math.sqrt(var_pop)

    # Sample variance (unbiased, ddof=1)
    if n > 1:
        v_sample = sum_sq_diff / (n - 1)
        var_sample: float | None = v_sample
        stdev_sample: float | None = math.sqrt(v_sample)
    else:
        var_sample = None
        stdev_sample = None

    q1, q2, q3 = quartiles(clean)
    iqr = q3 - q1
    outliers = detect_outliers(clean)

    return DescriptiveStats(
        count=n,
        sum=total,
        mean=mean_val,
        median=q2,
        min=min_val,
        max=max_val,
        range=val_range,
        variance_population=var_pop,
        variance_sample=var_sample,
        stdev_population=stdev_pop,
        stdev_sample=stdev_sample,
        q1=q1,
        q2=q2,
        q3=q3,
        iqr=iqr,
        outliers=outliers,
    )
