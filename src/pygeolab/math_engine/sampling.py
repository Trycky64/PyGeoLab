"""Sample safe functions into discontinuity-separated polylines for rendering."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from pygeolab.geometry import Point2D
from pygeolab.math_engine.evaluator import EvaluationError
from pygeolab.math_engine.functions import (
    FunctionObject,
    ParametricFunctionObject,
    PolarFunctionObject,
)


@dataclass(frozen=True, slots=True)
class SampledFunction:
    """Polyline pieces that may be rendered without crossing detected discontinuities."""

    segments: tuple[tuple[Point2D, ...], ...]


def sample_function(
    function: FunctionObject,
    x_min: float,
    x_max: float,
    *,
    samples: int = 800,
    variables: Mapping[str, float] | None = None,
    jump_factor: float = 40.0,
) -> SampledFunction:
    """Sample an interval and split on errors, non-finite values and large jumps."""
    if not math.isfinite(x_min) or not math.isfinite(x_max) or x_min >= x_max:
        raise ValueError("Intervalle de sampling invalide")
    if samples < 2:
        raise ValueError("Au moins deux échantillons sont nécessaires")
    domain_min, domain_max = x_min, x_max
    if function.domain is not None:
        domain_min = max(domain_min, function.domain[0])
        domain_max = min(domain_max, function.domain[1])
        if domain_min >= domain_max:
            return SampledFunction(())
    step = (domain_max - domain_min) / (samples - 1)
    pieces: list[tuple[Point2D, ...]] = []
    current: list[Point2D] = []
    previous_x: float | None = None
    previous_y: float | None = None
    typical_scale = 1.0
    for index in range(samples):
        x = domain_min + index * step
        try:
            y = function.evaluate(x, variables)
        except (EvaluationError, ValueError, ArithmeticError):
            if len(current) >= 2:
                pieces.append(tuple(current))
            current = []
            previous_x = None
            previous_y = None
            continue
        if previous_x is not None and previous_y is not None:
            jump = abs(y - previous_y)
            typical_scale = max(typical_scale, min(abs(y), abs(previous_y)), 1.0)
            discontinuity = jump > jump_factor * typical_scale
            midpoint_x = (previous_x + x) / 2
            try:
                midpoint_y = function.evaluate(midpoint_x, variables)
            except (EvaluationError, ValueError, ArithmeticError):
                discontinuity = True
            else:
                endpoint_scale = max(1.0, abs(previous_y), abs(y))
                nonlinear_jump = abs(midpoint_y - (previous_y + y) / 2)
                hidden_pole = (
                    previous_y * y < 0
                    and min(abs(previous_y), abs(y)) > 4.0
                    and abs(midpoint_y) > min(abs(previous_y), abs(y)) / 2
                )
                discontinuity = (
                    discontinuity or nonlinear_jump > jump_factor * endpoint_scale or hidden_pole
                )
            if discontinuity:
                if len(current) >= 2:
                    pieces.append(tuple(current))
                current = []
        current.append(Point2D(x, y))
        previous_x = x
        previous_y = y
    if len(current) >= 2:
        pieces.append(tuple(current))
    return SampledFunction(tuple(pieces))


def sample_parametric(
    curve: ParametricFunctionObject,
    *,
    samples: int = 800,
    variables: Mapping[str, float] | None = None,
    jump_factor: float = 40.0,
) -> SampledFunction:
    """Sample a parametric curve on [t_min, t_max] and split on discontinuities."""
    if samples < 2:
        raise ValueError("Au moins deux échantillons sont nécessaires")
    t_min, t_max = curve.t_min, curve.t_max
    step = (t_max - t_min) / (samples - 1)
    pieces: list[tuple[Point2D, ...]] = []
    current: list[Point2D] = []
    previous_t: float | None = None
    previous_pt: Point2D | None = None
    typical_scale = 1.0

    for index in range(samples):
        t = t_min + index * step
        try:
            pt = curve.evaluate(t, variables)
        except (EvaluationError, ValueError, ArithmeticError):
            if len(current) >= 2:
                pieces.append(tuple(current))
            current = []
            previous_t = None
            previous_pt = None
            continue

        if previous_t is not None and previous_pt is not None:
            dist = previous_pt.distance_to(pt)
            typical_scale = max(
                typical_scale,
                min(math.hypot(pt.x, pt.y), math.hypot(previous_pt.x, previous_pt.y)),
                1.0,
            )
            discontinuity = dist > jump_factor * typical_scale
            mid_t = (previous_t + t) / 2.0
            try:
                mid_pt = curve.evaluate(mid_t, variables)
            except (EvaluationError, ValueError, ArithmeticError):
                discontinuity = True
            else:
                endpoint_scale = max(
                    1.0, math.hypot(previous_pt.x, previous_pt.y), math.hypot(pt.x, pt.y)
                )
                linear_mid_x = (previous_pt.x + pt.x) / 2.0
                linear_mid_y = (previous_pt.y + pt.y) / 2.0
                nonlinear_jump = math.hypot(mid_pt.x - linear_mid_x, mid_pt.y - linear_mid_y)
                discontinuity = discontinuity or nonlinear_jump > jump_factor * endpoint_scale

            if discontinuity:
                if len(current) >= 2:
                    pieces.append(tuple(current))
                current = []

        current.append(pt)
        previous_t = t
        previous_pt = pt

    if len(current) >= 2:
        pieces.append(tuple(current))
    return SampledFunction(tuple(pieces))


def sample_polar(
    curve: PolarFunctionObject,
    samples: int = 400,
    variables: Mapping[str, float] | None = None,
    jump_factor: float = 40.0,
) -> SampledFunction:
    """Sample a polar curve on [theta_min, theta_max] and split on discontinuities."""
    if samples < 2:
        raise ValueError("Au moins deux échantillons sont nécessaires")
    theta_min, theta_max = curve.theta_min, curve.theta_max
    step = (theta_max - theta_min) / (samples - 1)
    pieces: list[tuple[Point2D, ...]] = []
    current: list[Point2D] = []
    previous_theta: float | None = None
    previous_pt: Point2D | None = None
    typical_scale = 1.0

    for index in range(samples):
        theta = theta_min + index * step
        try:
            pt = curve.evaluate(theta, variables)
        except (EvaluationError, ValueError, ArithmeticError):
            if len(current) >= 2:
                pieces.append(tuple(current))
            current = []
            previous_theta = None
            previous_pt = None
            continue

        if previous_theta is not None and previous_pt is not None:
            dist = previous_pt.distance_to(pt)
            typical_scale = max(
                typical_scale,
                min(math.hypot(pt.x, pt.y), math.hypot(previous_pt.x, previous_pt.y)),
                1.0,
            )
            discontinuity = dist > jump_factor * typical_scale
            mid_theta = (previous_theta + theta) / 2.0
            try:
                mid_pt = curve.evaluate(mid_theta, variables)
            except (EvaluationError, ValueError, ArithmeticError):
                discontinuity = True
            else:
                endpoint_scale = max(
                    1.0, math.hypot(previous_pt.x, previous_pt.y), math.hypot(pt.x, pt.y)
                )
                linear_mid_x = (previous_pt.x + pt.x) / 2.0
                linear_mid_y = (previous_pt.y + pt.y) / 2.0
                nonlinear_jump = math.hypot(mid_pt.x - linear_mid_x, mid_pt.y - linear_mid_y)
                discontinuity = discontinuity or nonlinear_jump > jump_factor * endpoint_scale

            if discontinuity:
                if len(current) >= 2:
                    pieces.append(tuple(current))
                current = []

        current.append(pt)
        previous_theta = theta
        previous_pt = pt

    if len(current) >= 2:
        pieces.append(tuple(current))
    return SampledFunction(tuple(pieces))
