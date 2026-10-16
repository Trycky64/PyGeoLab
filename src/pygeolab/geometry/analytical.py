"""Pure Euclidean analytical geometry calculations, representations and metric tolerances.

This module provides explicit analytical formulas for points, vectors, lines,
segments, rays, and circles, independent of Qt, canvas rendering, or UI logic.
All floating-point tolerances are documented and explicitly parameterized.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from pygeolab.geometry.conics import (
    Ellipse2D,
    Hyperbola2D,
    Parabola2D,
)
from pygeolab.geometry.primitives import (
    EPSILON,
    Circle2D,
    Line2D,
    Point2D,
    Ray2D,
    Segment2D,
    Vector2D,
)

# Explicit numerical tolerances
# EPSILON (1e-9): Absolute distance and coordinate tolerance for Euclidean space.
# ANGLE_EPSILON (1e-7): Angular tolerance in radians (~0.0000057 degrees).
ANGLE_EPSILON: float = 1e-7


def format_number(val: float, precision: int = 4) -> str:
    """Format a floating point number cleanly for mathematical equations."""
    rounded = round(val, precision)
    if abs(rounded) < 10 ** (-precision) or rounded == 0.0:
        return "0"
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.{precision}f}".rstrip("0").rstrip(".")


# ============================================================================
# Point-to-Point & Point-to-Line Metrics
# ============================================================================


def distance_point_to_point(p1: Point2D, p2: Point2D) -> float:
    """Return the Euclidean distance between two points."""
    return p1.distance_to(p2)


def squared_distance_point_to_point(p1: Point2D, p2: Point2D) -> float:
    """Return the squared Euclidean distance between two points."""
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return dx * dx + dy * dy


def midpoint(p1: Point2D, p2: Point2D) -> Point2D:
    """Return the midpoint between two points."""
    return Point2D((p1.x + p2.x) / 2.0, (p1.y + p2.y) / 2.0)


def distance_point_to_line(point: Point2D, line: Line2D) -> float:
    """Return the shortest distance from a point to an infinite line."""
    return line.distance(point)


def project_point_on_line(point: Point2D, line: Line2D) -> Point2D:
    """Return the orthogonal projection of a point onto an infinite line."""
    return line.project(point)


# ============================================================================
# Vector Metrics & Operations
# ============================================================================


def vector_norm(v: Vector2D) -> float:
    """Return the Euclidean norm (length) of a 2D vector."""
    return v.norm


def dot_product(u: Vector2D, v: Vector2D) -> float:
    """Return the dot (scalar) product of two 2D vectors: u.x * v.x + u.y * v.y."""
    return u.dot(v)


def determinant_2d(u: Vector2D, v: Vector2D) -> float:
    """Return the 2D determinant (cross product): u.x * v.y - u.y * v.x."""
    return u.cross(v)


def angle_between_vectors(
    u: Vector2D,
    v: Vector2D,
    signed: bool = False,
    tolerance: float = EPSILON,
) -> float:
    """Return the angle between two vectors in radians.

    If signed is True: returns angle in (-pi, pi] (positive counter-clockwise from u to v).
    If signed is False: returns acute/obtuse angle in [0, pi].
    Returns 0.0 if either vector has norm below tolerance.
    """
    norm_u = u.norm
    norm_v = v.norm
    if norm_u <= tolerance or norm_v <= tolerance:
        return 0.0

    if signed:
        det = determinant_2d(u, v)
        dot = dot_product(u, v)
        return math.atan2(det, dot)

    cos_theta = dot_product(u, v) / (norm_u * norm_v)
    clamped_cos = max(-1.0, min(1.0, cos_theta))
    return math.acos(clamped_cos)


def are_vectors_collinear(
    u: Vector2D,
    v: Vector2D,
    tolerance: float = EPSILON,
) -> bool:
    """Check if two vectors are collinear (det(u, v) ~ 0)."""
    norm_prod = u.norm * v.norm
    scale = max(1.0, norm_prod)
    return abs(determinant_2d(u, v)) <= tolerance * scale


def are_vectors_orthogonal(
    u: Vector2D,
    v: Vector2D,
    tolerance: float = EPSILON,
) -> bool:
    """Check if two vectors are orthogonal (u . v ~ 0)."""
    norm_prod = u.norm * v.norm
    scale = max(1.0, norm_prod)
    return abs(dot_product(u, v)) <= tolerance * scale


def are_points_collinear(
    p1: Point2D,
    p2: Point2D,
    p3: Point2D,
    tolerance: float = EPSILON,
) -> bool:
    """Check if three points are collinear."""
    u = Vector2D.between(p1, p2)
    v = Vector2D.between(p1, p3)
    return are_vectors_collinear(u, v, tolerance=tolerance)


# ============================================================================
# Line Equations & Relationships
# ============================================================================


@dataclass(frozen=True, slots=True)
class LineAnalyticalForm:
    """Comprehensive analytical representation of an infinite 2D line."""

    a: float
    b: float
    c: float
    slope: float | None
    y_intercept: float | None
    x_intercept: float | None
    is_vertical: bool
    is_horizontal: bool
    cartesian_equation: str
    slope_intercept_equation: str


def line_slope(line: Line2D, tolerance: float = EPSILON) -> float | None:
    """Return the slope m of the line, or None if the line is vertical."""
    if abs(line.b) <= tolerance:
        return None
    return -line.a / line.b


def line_y_intercept(line: Line2D, tolerance: float = EPSILON) -> float | None:
    """Return the y-intercept p of the line, or None if the line is vertical."""
    if abs(line.b) <= tolerance:
        return None
    return -line.c / line.b


def line_x_intercept(line: Line2D, tolerance: float = EPSILON) -> float | None:
    """Return the x-intercept of the line, or None if the line is horizontal."""
    if abs(line.a) <= tolerance:
        return None
    return -line.c / line.a


def line_is_vertical(line: Line2D, tolerance: float = EPSILON) -> bool:
    """Return True if the line is vertical (b ~ 0)."""
    return abs(line.b) <= tolerance


def line_is_horizontal(line: Line2D, tolerance: float = EPSILON) -> bool:
    """Return True if the line is horizontal (a ~ 0)."""
    return abs(line.a) <= tolerance


def format_cartesian_line(line: Line2D, precision: int = 4) -> str:
    """Format line equation as ax + by + c = 0."""
    a_rnd = round(line.a, precision)
    b_rnd = round(line.b, precision)
    c_rnd = round(line.c, precision)

    # Normalize sign so leading nonzero coefficient is positive
    if a_rnd < 0 or (a_rnd == 0 and b_rnd < 0):
        a_rnd, b_rnd, c_rnd = -a_rnd, -b_rnd, -c_rnd

    parts: list[str] = []

    # X term
    if abs(a_rnd) > 10 ** (-precision):
        if a_rnd == 1.0:
            parts.append("x")
        elif a_rnd == -1.0:
            parts.append("-x")
        else:
            parts.append(f"{format_number(a_rnd, precision)}x")

    # Y term
    if abs(b_rnd) > 10 ** (-precision):
        if not parts:
            if b_rnd == 1.0:
                parts.append("y")
            elif b_rnd == -1.0:
                parts.append("-y")
            else:
                parts.append(f"{format_number(b_rnd, precision)}y")
        else:
            sign = " + " if b_rnd > 0 else " - "
            val = abs(b_rnd)
            term = "y" if val == 1.0 else f"{format_number(val, precision)}y"
            parts.append(f"{sign}{term}")

    # Constant term
    if abs(c_rnd) > 10 ** (-precision) or not parts:
        if not parts:
            parts.append(format_number(c_rnd, precision))
        else:
            sign = " + " if c_rnd > 0 else " - "
            parts.append(f"{sign}{format_number(abs(c_rnd), precision)}")

    return "".join(parts) + " = 0"


def format_slope_intercept_line(
    line: Line2D, precision: int = 4, tolerance: float = EPSILON
) -> str:
    """Format line equation in slope-intercept form (y = mx + p or x = k)."""
    if line_is_vertical(line, tolerance):
        x_int = line_x_intercept(line, tolerance)
        val = 0.0 if x_int is None else x_int
        return f"x = {format_number(val, precision)}"

    m = line_slope(line, tolerance) or 0.0
    p = line_y_intercept(line, tolerance) or 0.0

    m_rnd = round(m, precision)
    p_rnd = round(p, precision)

    if abs(m_rnd) <= 10 ** (-precision):
        return f"y = {format_number(p_rnd, precision)}"

    if m_rnd == 1.0:
        m_str = "x"
    elif m_rnd == -1.0:
        m_str = "-x"
    else:
        m_str = f"{format_number(m_rnd, precision)}x"

    if abs(p_rnd) <= 10 ** (-precision):
        return f"y = {m_str}"

    sign = " + " if p_rnd > 0 else " - "
    return f"y = {m_str}{sign}{format_number(abs(p_rnd), precision)}"


def analyze_line(
    line: Line2D, precision: int = 4, tolerance: float = EPSILON
) -> LineAnalyticalForm:
    """Compute the full analytical breakdown of a line."""
    vert = line_is_vertical(line, tolerance)
    horiz = line_is_horizontal(line, tolerance)
    m = line_slope(line, tolerance)
    y_int = line_y_intercept(line, tolerance)
    x_int = line_x_intercept(line, tolerance)
    cart = format_cartesian_line(line, precision)
    slope_int = format_slope_intercept_line(line, precision, tolerance)

    return LineAnalyticalForm(
        a=line.a,
        b=line.b,
        c=line.c,
        slope=m,
        y_intercept=y_int,
        x_intercept=x_int,
        is_vertical=vert,
        is_horizontal=horiz,
        cartesian_equation=cart,
        slope_intercept_equation=slope_int,
    )


def angle_between_lines(
    l1: Line2D,
    l2: Line2D,
    tolerance: float = EPSILON,
) -> float:
    """Return the acute angle in [0, pi/2] between two infinite lines in radians."""
    # cos(theta) = |a1*a2 + b1*b2| / (norm(n1) * norm(n2))
    # Line2D normals are normalized to unit length, so norm(n1) = norm(n2) = 1
    dot_normal = abs(l1.a * l2.a + l1.b * l2.b)
    clamped_cos = max(0.0, min(1.0, dot_normal))
    return math.acos(clamped_cos)


def are_lines_parallel(
    l1: Line2D,
    l2: Line2D,
    tolerance: float = EPSILON,
) -> bool:
    """Check if two lines are parallel (|a1*b2 - a2*b1| <= tolerance)."""
    cross = abs(l1.a * l2.b - l1.b * l2.a)
    return cross <= tolerance


def are_lines_orthogonal(
    l1: Line2D,
    l2: Line2D,
    tolerance: float = EPSILON,
) -> bool:
    """Check if two lines are perpendicular (|a1*a2 + b1*b2| <= tolerance)."""
    dot = abs(l1.a * l2.a + l1.b * l2.b)
    return dot <= tolerance


# ============================================================================
# Circle Equations & Metrics
# ============================================================================


@dataclass(frozen=True, slots=True)
class CircleAnalyticalForm:
    """Comprehensive analytical representation of a 2D circle."""

    center: Point2D
    radius: float
    perimeter: float
    area: float
    canonical_equation: str
    general_equation: str


def format_circle_canonical(circle: Circle2D, precision: int = 4) -> str:
    """Format canonical circle equation: (x - x0)² + (y - y0)² = R²."""
    x0 = circle.center.x
    y0 = circle.center.y
    r = circle.radius

    if abs(x0) <= 10 ** (-precision):
        x_part = "x²"
    elif x0 > 0:
        x_part = f"(x - {format_number(x0, precision)})²"
    else:
        x_part = f"(x + {format_number(abs(x0), precision)})²"

    if abs(y0) <= 10 ** (-precision):
        y_part = "y²"
    elif y0 > 0:
        y_part = f"(y - {format_number(y0, precision)})²"
    else:
        y_part = f"(y + {format_number(abs(y0), precision)})²"

    r_sq = r * r
    return f"{x_part} + {y_part} = {format_number(r_sq, precision)}"


def format_circle_general(circle: Circle2D, precision: int = 4) -> str:
    """Format general circle equation: x² + y² + Dx + Ey + F = 0."""
    x0 = circle.center.x
    y0 = circle.center.y
    r = circle.radius

    d = -2.0 * x0
    e = -2.0 * y0
    f = x0 * x0 + y0 * y0 - r * r

    parts = ["x² + y²"]

    if abs(d) > 10 ** (-precision):
        sign = " + " if d > 0 else " - "
        val = abs(d)
        term = "x" if val == 1.0 else f"{format_number(val, precision)}x"
        parts.append(f"{sign}{term}")

    if abs(e) > 10 ** (-precision):
        sign = " + " if e > 0 else " - "
        val = abs(e)
        term = "y" if val == 1.0 else f"{format_number(val, precision)}y"
        parts.append(f"{sign}{term}")

    if abs(f) > 10 ** (-precision):
        sign = " + " if f > 0 else " - "
        parts.append(f"{sign}{format_number(abs(f), precision)}")

    return "".join(parts) + " = 0"


def circle_perimeter(circle: Circle2D) -> float:
    """Return the circumference 2 * pi * R of the circle."""
    return 2.0 * math.pi * circle.radius


def circle_area(circle: Circle2D) -> float:
    """Return the disk area pi * R² of the circle."""
    return math.pi * circle.radius * circle.radius


def analyze_circle(circle: Circle2D, precision: int = 4) -> CircleAnalyticalForm:
    """Compute the full analytical breakdown of a circle."""
    return CircleAnalyticalForm(
        center=circle.center,
        radius=circle.radius,
        perimeter=circle.perimeter,
        area=circle.area,
        canonical_equation=format_circle_canonical(circle, precision),
        general_equation=format_circle_general(circle, precision),
    )


# ============================================================================
# Segment & Ray Analytical Breakdown
# ============================================================================


def analyze_segment(segment: Segment2D, precision: int = 4) -> dict[str, str | float]:
    """Compute analytical properties of a segment."""
    mid = midpoint(segment.start, segment.end)
    vec = Vector2D.between(segment.start, segment.end)
    line = Line2D.from_points(segment.start, segment.end)
    return {
        "length": segment.length,
        "midpoint_x": mid.x,
        "midpoint_y": mid.y,
        "dx": vec.x,
        "dy": vec.y,
        "line_equation": format_cartesian_line(line, precision) if line else "—",
        "slope_intercept": format_slope_intercept_line(line, precision) if line else "—",
    }


def analyze_ray(ray: Ray2D, precision: int = 4) -> dict[str, str | float]:
    """Compute analytical properties of a ray."""
    vec = Vector2D.between(ray.start, ray.through)
    line = ray.line
    return {
        "origin_x": ray.start.x,
        "origin_y": ray.start.y,
        "dx": vec.x,
        "dy": vec.y,
        "line_equation": format_cartesian_line(line, precision) if line else "—",
        "slope_intercept": format_slope_intercept_line(line, precision) if line else "—",
    }


# ============================================================================
# Conics Analytical Representation
# ============================================================================


def format_ellipse_equation(ellipse: Ellipse2D, precision: int = 4) -> str:
    """Format canonical ellipse equation: (x - x0)²/a² + (y - y0)²/b² = 1."""
    a_sq = ellipse.a * ellipse.a
    b_sq = ellipse.b * ellipse.b
    x0, y0 = ellipse.center.x, ellipse.center.y
    if abs(x0) <= 10 ** (-precision):
        x_term = "x²"
    elif x0 > 0:
        x_term = f"(x - {format_number(x0, precision)})²"
    else:
        x_term = f"(x + {format_number(abs(x0), precision)})²"

    if abs(y0) <= 10 ** (-precision):
        y_term = "y²"
    elif y0 > 0:
        y_term = f"(y - {format_number(y0, precision)})²"
    else:
        y_term = f"(y + {format_number(abs(y0), precision)})²"

    a_str = format_number(a_sq, precision)
    b_str = format_number(b_sq, precision)
    if abs(ellipse.angle) <= 1e-4:
        return f"{x_term}/{a_str} + {y_term}/{b_str} = 1"
    ang_deg = math.degrees(ellipse.angle)
    return f"{x_term}/{a_str} + {y_term}/{b_str} = 1 (rot {format_number(ang_deg, 1)}°)"


def format_parabola_equation(parabola: Parabola2D, precision: int = 4) -> str:
    """Format parabola canonical form: y'² = 2px."""
    p = parabola.parameter
    return f"y'² = 2px (p = {format_number(p, precision)})"


def format_hyperbola_equation(hyperbola: Hyperbola2D, precision: int = 4) -> str:
    """Format canonical hyperbola equation: (x - x0)²/a² - (y - y0)²/b² = 1."""
    a_sq = hyperbola.a * hyperbola.a
    b_sq = hyperbola.b * hyperbola.b
    x0, y0 = hyperbola.center.x, hyperbola.center.y
    if abs(x0) <= 10 ** (-precision):
        x_term = "x²"
    elif x0 > 0:
        x_term = f"(x - {format_number(x0, precision)})²"
    else:
        x_term = f"(x + {format_number(abs(x0), precision)})²"

    if abs(y0) <= 10 ** (-precision):
        y_term = "y²"
    elif y0 > 0:
        y_term = f"(y - {format_number(y0, precision)})²"
    else:
        y_term = f"(y + {format_number(abs(y0), precision)})²"

    a_str = format_number(a_sq, precision)
    b_str = format_number(b_sq, precision)
    if abs(hyperbola.angle) <= 1e-4:
        return f"{x_term}/{a_str} - {y_term}/{b_str} = 1"
    ang_deg = math.degrees(hyperbola.angle)
    return f"{x_term}/{a_str} - {y_term}/{b_str} = 1 (rot {format_number(ang_deg, 1)}°)"


def analyze_ellipse(ellipse: Ellipse2D, precision: int = 4) -> dict[str, str | float]:
    """Compute complete analytical properties of an ellipse."""
    f1, f2 = ellipse.foci
    cx = format_number(ellipse.center.x, precision)
    cy = format_number(ellipse.center.y, precision)
    f1_str = f"F1({format_number(f1.x, precision)}, {format_number(f1.y, precision)})"
    f2_str = f"F2({format_number(f2.x, precision)}, {format_number(f2.y, precision)})"
    return {
        "equation": format_ellipse_equation(ellipse, precision),
        "center": f"({cx}, {cy})",
        "a": ellipse.a,
        "b": ellipse.b,
        "c": ellipse.linear_eccentricity,
        "eccentricity": ellipse.eccentricity,
        "foci": f"{f1_str}, {f2_str}",
        "perimeter": ellipse.perimeter,
        "area": ellipse.area,
    }


def analyze_parabola(parabola: Parabola2D, precision: int = 4) -> dict[str, str | float]:
    """Compute complete analytical properties of a parabola."""
    v = parabola.vertex
    f = parabola.focus
    d_eq = format_cartesian_line(parabola.directrix, precision)
    return {
        "equation": format_parabola_equation(parabola, precision),
        "vertex": f"({format_number(v.x, precision)}, {format_number(v.y, precision)})",
        "focus": f"({format_number(f.x, precision)}, {format_number(f.y, precision)})",
        "parameter": parabola.parameter,
        "directrix": d_eq,
    }


def analyze_hyperbola(hyperbola: Hyperbola2D, precision: int = 4) -> dict[str, str | float]:
    """Compute complete analytical properties of a hyperbola."""
    c = hyperbola.center
    f1, f2 = hyperbola.focus1, hyperbola.focus2
    v1, v2 = hyperbola.vertices
    asym1, asym2 = hyperbola.asymptotes
    cx = format_number(c.x, precision)
    cy = format_number(c.y, precision)
    f1_str = f"F1({format_number(f1.x, precision)}, {format_number(f1.y, precision)})"
    f2_str = f"F2({format_number(f2.x, precision)}, {format_number(f2.y, precision)})"
    v1_str = f"V1({format_number(v1.x, precision)}, {format_number(v1.y, precision)})"
    v2_str = f"V2({format_number(v2.x, precision)}, {format_number(v2.y, precision)})"
    return {
        "equation": format_hyperbola_equation(hyperbola, precision),
        "center": f"({cx}, {cy})",
        "a": hyperbola.a,
        "b": hyperbola.b,
        "c": hyperbola.linear_eccentricity,
        "eccentricity": hyperbola.eccentricity,
        "foci": f"{f1_str}, {f2_str}",
        "vertices": f"{v1_str}, {v2_str}",
        "asymptote1": format_cartesian_line(asym1, precision),
        "asymptote2": format_cartesian_line(asym2, precision),
    }
