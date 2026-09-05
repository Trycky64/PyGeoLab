"""Documented deterministic numerical-analysis algorithms for safe functions."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from pygeolab.math_engine.evaluator import EvaluationError
from pygeolab.math_engine.functions import FunctionObject


def derivative(
    function: FunctionObject,
    x: float,
    variables: Mapping[str, float] | None = None,
    step: float | None = None,
) -> float:
    """Estimate f'(x) with a symmetric finite difference and scale-aware step."""
    h = step if step is not None else math.sqrt(math.ulp(1.0)) * max(1.0, abs(x))
    if not math.isfinite(h) or h <= 0:
        raise ValueError("Le pas de dérivation doit être positif et fini")
    return (function.evaluate(x + h, variables) - function.evaluate(x - h, variables)) / (2 * h)


def integrate(
    function: FunctionObject,
    start: float,
    end: float,
    variables: Mapping[str, float] | None = None,
    intervals: int = 512,
) -> float:
    """Integrate on a finite interval using composite Simpson quadrature."""
    if not math.isfinite(start) or not math.isfinite(end):
        raise ValueError("Les bornes d'intégration doivent être finies")
    if intervals < 2:
        raise ValueError("Au moins deux sous-intervalles sont nécessaires")
    if intervals % 2:
        intervals += 1
    if start == end:
        return 0.0
    sign = 1.0
    if end < start:
        start, end = end, start
        sign = -1.0
    h = (end - start) / intervals
    total = function.evaluate(start, variables) + function.evaluate(end, variables)
    for index in range(1, intervals):
        coefficient = 4 if index % 2 else 2
        total += coefficient * function.evaluate(start + index * h, variables)
    return sign * total * h / 3.0


def find_roots(
    function: FunctionObject,
    start: float,
    end: float,
    variables: Mapping[str, float] | None = None,
    samples: int = 512,
    tolerance: float = 1e-9,
) -> tuple[float, ...]:
    """Find sign-changing and sampled exact roots, refining brackets by bisection."""
    if start >= end or samples < 2 or tolerance <= 0:
        raise ValueError("Intervalle, échantillonnage ou tolérance invalide")
    roots: list[float] = []
    previous_x: float | None = None
    previous_y: float | None = None
    for index in range(samples + 1):
        x = start + (end - start) * index / samples
        try:
            y = function.evaluate(x, variables)
        except (ValueError, EvaluationError, ArithmeticError):
            previous_x = previous_y = None
            continue
        if abs(y) <= tolerance:
            _append_unique(roots, x, tolerance * 10)
        if previous_x is not None and previous_y is not None and previous_y * y < 0:
            root = _bisect(function, previous_x, x, variables, tolerance)
            _append_unique(roots, root, tolerance * 10)
        previous_x, previous_y = x, y
    return tuple(roots)


def _bisect(
    function: FunctionObject,
    left: float,
    right: float,
    variables: Mapping[str, float] | None,
    tolerance: float,
) -> float:
    left_y = function.evaluate(left, variables)
    for _ in range(100):
        middle = (left + right) / 2
        middle_y = function.evaluate(middle, variables)
        if abs(middle_y) <= tolerance or right - left <= tolerance:
            return middle
        if left_y * middle_y <= 0:
            right = middle
        else:
            left, left_y = middle, middle_y
    return (left + right) / 2


def _append_unique(values: list[float], value: float, tolerance: float) -> None:
    if not values or abs(values[-1] - value) > tolerance:
        values.append(value)


@dataclass(frozen=True, slots=True)
class Extremum:
    """One numerically detected local minimum or maximum."""

    x: float
    y: float
    kind: str


def extrema(
    function: FunctionObject,
    start: float,
    end: float,
    variables: Mapping[str, float] | None = None,
    samples: int = 512,
) -> tuple[Extremum, ...]:
    """Detect local extrema from sampled three-point neighborhoods and refine parabolically."""
    if start >= end or samples < 3:
        raise ValueError("Intervalle ou échantillonnage invalide")
    points: list[tuple[float, float]] = []
    for index in range(samples + 1):
        x = start + (end - start) * index / samples
        try:
            points.append((x, function.evaluate(x, variables)))
        except (ValueError, EvaluationError, ArithmeticError):
            points.append((x, math.nan))
    result: list[Extremum] = []
    for index in range(1, len(points) - 1):
        x0, y0 = points[index - 1]
        x1, y1 = points[index]
        x2, y2 = points[index + 1]
        if not all(math.isfinite(value) for value in (y0, y1, y2)):
            continue
        kind = "minimum" if y1 < y0 and y1 < y2 else "maximum" if y1 > y0 and y1 > y2 else ""
        if not kind:
            continue
        denominator = y0 - 2 * y1 + y2
        x = x1
        if denominator != 0:
            x = x1 + 0.5 * (y0 - y2) / denominator * (x2 - x1)
        try:
            y = function.evaluate(x, variables)
        except (ValueError, EvaluationError, ArithmeticError):
            x, y = x1, y1
        result.append(Extremum(x, y, kind))
    return tuple(result)


def intersections(
    first: FunctionObject,
    second: FunctionObject,
    start: float,
    end: float,
    variables: Mapping[str, float] | None = None,
    samples: int = 512,
    tolerance: float = 1e-9,
) -> tuple[tuple[float, float], ...]:
    """Find intersections by scanning and bisecting sign changes of f(x)-g(x)."""
    if start >= end or samples < 2 or tolerance <= 0:
        raise ValueError("Intervalle, échantillonnage ou tolérance invalide")

    def difference(x: float) -> float:
        return first.evaluate(x, variables) - second.evaluate(x, variables)

    roots: list[float] = []
    previous_x: float | None = None
    previous_y: float | None = None
    for index in range(samples + 1):
        x = start + (end - start) * index / samples
        try:
            y = difference(x)
        except (ValueError, EvaluationError, ArithmeticError):
            previous_x = previous_y = None
            continue
        if abs(y) <= tolerance:
            _append_unique(roots, x, tolerance * 10)
        if previous_x is not None and previous_y is not None and previous_y * y < 0:
            left, right = previous_x, x
            left_y = previous_y
            for _ in range(100):
                middle = (left + right) / 2
                middle_y = difference(middle)
                if abs(middle_y) <= tolerance or right - left <= tolerance:
                    break
                if left_y * middle_y <= 0:
                    right = middle
                else:
                    left, left_y = middle, middle_y
            _append_unique(roots, (left + right) / 2, tolerance * 10)
        previous_x, previous_y = x, y
    return tuple((x, first.evaluate(x, variables)) for x in roots)
