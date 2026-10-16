"""Immutable 2D Conic Euclidean primitives: Ellipses, Parabolas, and Hyperbolas.

These models represent true geometric conics independently of canvas rendering or Qt.
Degenerate configurations (coincident foci, points on directrices, singular vertices)
are validated at construction and return None from factory methods.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from pygeolab.geometry.primitives import (
    EPSILON,
    Line2D,
    Point2D,
    Vector2D,
)


def _finite(*values: float) -> None:
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Les valeurs géométriques doivent être finies")


# ============================================================================
# Ellipse2D
# ============================================================================


@dataclass(frozen=True, slots=True)
class Ellipse2D:
    """An immutable Euclidean ellipse defined by center, semi-axes, and rotation.

    a: semi-major axis (a > 0)
    b: semi-minor axis (0 < b <= a)
    angle: rotation of the major axis relative to the X axis in radians
    """

    center: Point2D
    a: float
    b: float
    angle: float = 0.0

    def __post_init__(self) -> None:
        _finite(self.a, self.b, self.angle)
        if self.a <= 0 or self.b <= 0:
            raise ValueError("Les demi-axes de l'ellipse doivent être strictement positifs")

    @classmethod
    def from_foci_and_point(
        cls, focus1: Point2D, focus2: Point2D, point: Point2D
    ) -> Ellipse2D | None:
        """Construct an ellipse from two focal points and one boundary point.

        Returns None if foci and point are collinear with the point between foci
        (degenerate segment), or if focal distance >= 2a.
        """
        dist1 = focus1.distance_to(point)
        dist2 = focus2.distance_to(point)
        two_a = dist1 + dist2
        two_c = focus1.distance_to(focus2)

        if two_a <= two_c + EPSILON or two_a <= EPSILON:
            return None

        a = two_a / 2.0
        c = two_c / 2.0
        b_sq = a * a - c * c
        if b_sq <= 0:
            return None
        b = math.sqrt(b_sq)

        center = Point2D((focus1.x + focus2.x) / 2.0, (focus1.y + focus2.y) / 2.0)
        angle = math.atan2(focus2.y - focus1.y, focus2.x - focus1.x)
        return cls(center=center, a=a, b=b, angle=angle)

    @classmethod
    def from_center_axes(
        cls,
        center: Point2D,
        major_axis_point: Point2D,
        minor_radius_or_point: float | Point2D,
    ) -> Ellipse2D | None:
        """Construct an ellipse from center, a major axis endpoint, and minor radius/point."""
        a = center.distance_to(major_axis_point)
        if a <= EPSILON:
            return None

        angle = math.atan2(major_axis_point.y - center.y, major_axis_point.x - center.x)

        if isinstance(minor_radius_or_point, Point2D):
            b = center.distance_to(minor_radius_or_point)
        else:
            b = float(minor_radius_or_point)

        if b <= EPSILON:
            return None

        # Normalize so a is major axis (a >= b)
        if b > a:
            return cls(center=center, a=b, b=a, angle=angle + math.pi / 2.0)
        return cls(center=center, a=a, b=b, angle=angle)

    @property
    def linear_eccentricity(self) -> float:
        """Focal distance c from center to each focus: c = sqrt(a^2 - b^2)."""
        diff = self.a * self.a - self.b * self.b
        return math.sqrt(max(0.0, diff))

    @property
    def c(self) -> float:
        """Focal distance c (alias for linear_eccentricity)."""
        return self.linear_eccentricity

    @property
    def eccentricity(self) -> float:
        """First eccentricity e = c / a in [0, 1). Zero represents a circle."""
        return self.linear_eccentricity / self.a

    @property
    def foci(self) -> tuple[Point2D, Point2D]:
        """The two focal points of the ellipse."""
        c = self.linear_eccentricity
        cos_ang = math.cos(self.angle)
        sin_ang = math.sin(self.angle)
        dx = c * cos_ang
        dy = c * sin_ang
        f1 = Point2D(self.center.x - dx, self.center.y - dy)
        f2 = Point2D(self.center.x + dx, self.center.y + dy)
        return (f1, f2)

    @property
    def area(self) -> float:
        """Area of the enclosed ellipse: pi * a * b."""
        return math.pi * self.a * self.b

    @property
    def perimeter(self) -> float:
        """Perimeter approximated using Ramanujan's formula (accuracy < 1e-5)."""
        a, b = self.a, self.b
        h = ((a - b) ** 2) / ((a + b) ** 2)
        return math.pi * (a + b) * (1.0 + (3.0 * h) / (10.0 + math.sqrt(4.0 - 3.0 * h)))

    @property
    def bounding_box(self) -> tuple[float, float, float, float]:
        """Exact bounding box (xmin, ymin, xmax, ymax) accounting for rotation."""
        cos_ang = math.cos(self.angle)
        sin_ang = math.sin(self.angle)
        dx = math.hypot(self.a * cos_ang, self.b * sin_ang)
        dy = math.hypot(self.a * sin_ang, self.b * cos_ang)
        return (
            self.center.x - dx,
            self.center.y - dy,
            self.center.x + dx,
            self.center.y + dy,
        )

    def point_at(self, t: float) -> Point2D:
        """Evaluate a point on the ellipse at parametric angle t in radians."""
        cos_t = math.cos(t)
        sin_t = math.sin(t)
        cos_phi = math.cos(self.angle)
        sin_phi = math.sin(self.angle)
        x = self.center.x + self.a * cos_t * cos_phi - self.b * sin_t * sin_phi
        y = self.center.y + self.a * cos_t * sin_phi + self.b * sin_t * cos_phi
        return Point2D(x, y)

    def sample(self, num_points: int = 120) -> tuple[Point2D, ...]:
        """Sample discrete boundary points for rendering or hit testing."""
        points: list[Point2D] = []
        step = (2.0 * math.pi) / num_points
        for i in range(num_points):
            points.append(self.point_at(i * step))
        return tuple(points)

    def distance_to(self, point: Point2D) -> float:
        """Approximate distance from a point to the ellipse boundary."""
        f1, f2 = self.foci
        dist_sum = point.distance_to(f1) + point.distance_to(f2)
        # Scaled deviation from focal definition |d1 + d2 - 2a|
        # Near the boundary, gradient norm is ~2
        return abs(dist_sum - 2.0 * self.a) / 2.0

    def contains(self, point: Point2D, tolerance: float = EPSILON) -> bool:
        """Check if point lies on the ellipse boundary within tolerance."""
        return self.distance_to(point) <= tolerance


# ============================================================================
# Parabola2D
# ============================================================================


@dataclass(frozen=True, slots=True)
class Parabola2D:
    """An immutable Euclidean parabola defined by its focal point and directrix line.

    The curve satisfies d(P, focus) == d(P, directrix).
    """

    focus: Point2D
    directrix: Line2D

    def __post_init__(self) -> None:
        dist = self.directrix.distance(self.focus)
        if dist <= EPSILON:
            raise ValueError("Le foyer ne peut pas appartenir à la directrice")

    @classmethod
    def from_focus_and_directrix(cls, focus: Point2D, directrix: Line2D) -> Parabola2D | None:
        """Construct a parabola, returning None if focus lies on directrix."""
        if directrix.distance(focus) <= EPSILON:
            return None
        return cls(focus=focus, directrix=directrix)

    @property
    def parameter(self) -> float:
        """Distance p from focus to directrix line: p = d(F, D)."""
        return self.directrix.distance(self.focus)

    @property
    def p(self) -> float:
        """Focal parameter p (alias for parameter)."""
        return self.parameter

    @property
    def vertex(self) -> Point2D:
        """The vertex V of the parabola (midpoint between focus and projected directrix)."""
        proj = self.directrix.project(self.focus)
        return Point2D((self.focus.x + proj.x) / 2.0, (self.focus.y + proj.y) / 2.0)

    @property
    def axis_direction(self) -> Vector2D:
        """Unit vector pointing from directrix projection to focus along symmetry axis."""
        proj = self.directrix.project(self.focus)
        vec = Vector2D.between(proj, self.focus).normalized()
        assert vec is not None
        return vec

    @property
    def tangent_direction(self) -> Vector2D:
        """Unit vector orthogonal to axis direction (tangent at vertex)."""
        axis = self.axis_direction
        return Vector2D(-axis.y, axis.x)

    def point_at_param(self, t: float) -> Point2D:
        """Evaluate point at local transverse coordinate t: P(t) = V + u*(t^2/(2p)) + v*t."""
        p = self.parameter
        v = self.vertex
        u_axis = self.axis_direction
        v_tan = self.tangent_direction
        s_axis = (t * t) / (2.0 * p)
        x = v.x + s_axis * u_axis.x + t * v_tan.x
        y = v.y + s_axis * u_axis.y + t * v_tan.y
        return Point2D(x, y)

    def distance_to(self, point: Point2D) -> float:
        """Orthogonal distance metric based on focal-directrix equality: |d(P, F) - d(P, D)|."""
        d_f = point.distance_to(self.focus)
        d_d = self.directrix.distance(point)
        return abs(d_f - d_d)

    def sample_in_range(
        self, t_min: float, t_max: float, num_points: int = 100
    ) -> tuple[Point2D, ...]:
        """Sample parabolic arc for t in [t_min, t_max]."""
        if num_points < 2:
            num_points = 2
        step = (t_max - t_min) / (num_points - 1)
        return tuple(self.point_at_param(t_min + i * step) for i in range(num_points))


# ============================================================================
# Hyperbola2D
# ============================================================================


@dataclass(frozen=True, slots=True)
class Hyperbola2D:
    """An immutable Euclidean hyperbola defined by two foci and transverse semi-axis a.

    The curve satisfies |d(P, F1) - d(P, F2)| == 2a with 0 < a < c = d(F1, F2)/2.
    """

    focus1: Point2D
    focus2: Point2D
    a: float

    def __post_init__(self) -> None:
        _finite(self.a)
        two_c = self.focus1.distance_to(self.focus2)
        c = two_c / 2.0
        if self.a <= 0 or self.a >= c:
            raise ValueError("Le demi-axe 'a' d'une hyperbole doit vérifier 0 < a < c")

    @classmethod
    def from_foci_and_point(
        cls, focus1: Point2D, focus2: Point2D, point: Point2D
    ) -> Hyperbola2D | None:
        """Construct a hyperbola passing through a given point.

        Returns None if 2a <= 0 or 2a >= 2c.
        """
        dist1 = focus1.distance_to(point)
        dist2 = focus2.distance_to(point)
        two_a = abs(dist1 - dist2)
        two_c = focus1.distance_to(focus2)

        if two_a <= EPSILON or two_a >= two_c - EPSILON:
            return None

        return cls(focus1=focus1, focus2=focus2, a=two_a / 2.0)

    @classmethod
    def from_foci_and_parameter(
        cls, focus1: Point2D, focus2: Point2D, a: float
    ) -> Hyperbola2D | None:
        """Construct a hyperbola with explicit semi-axis a."""
        two_c = focus1.distance_to(focus2)
        c = two_c / 2.0
        if a <= EPSILON or a >= c - EPSILON:
            return None
        return cls(focus1=focus1, focus2=focus2, a=a)

    @property
    def linear_eccentricity(self) -> float:
        """Focal semi-distance c = d(F1, F2) / 2."""
        return self.focus1.distance_to(self.focus2) / 2.0

    @property
    def c(self) -> float:
        """Focal distance c (alias for linear_eccentricity)."""
        return self.linear_eccentricity

    @property
    def b(self) -> float:
        """Conjugate semi-axis b = sqrt(c^2 - a^2)."""
        c = self.linear_eccentricity
        return math.sqrt(max(0.0, c * c - self.a * self.a))

    @property
    def center(self) -> Point2D:
        """Center of symmetry O = midpoint(F1, F2)."""
        return Point2D(
            (self.focus1.x + self.focus2.x) / 2.0,
            (self.focus1.y + self.focus2.y) / 2.0,
        )

    @property
    def eccentricity(self) -> float:
        """Eccentricity e = c / a > 1."""
        return self.linear_eccentricity / self.a

    @property
    def angle(self) -> float:
        """Focal axis angle from focus1 to focus2 in radians."""
        return math.atan2(self.focus2.y - self.focus1.y, self.focus2.x - self.focus1.x)

    @property
    def axis_direction(self) -> Vector2D:
        """Unit vector pointing along the focal transverse axis."""
        vec = Vector2D.between(self.focus1, self.focus2).normalized()
        assert vec is not None
        return vec

    @property
    def conjugate_direction(self) -> Vector2D:
        """Unit vector perpendicular to the focal axis."""
        axis = self.axis_direction
        return Vector2D(-axis.y, axis.x)

    @property
    def vertices(self) -> tuple[Point2D, Point2D]:
        """The two real vertices located at distance a from center."""
        c_pt = self.center
        u = self.axis_direction
        v1 = Point2D(c_pt.x - self.a * u.x, c_pt.y - self.a * u.y)
        v2 = Point2D(c_pt.x + self.a * u.x, c_pt.y + self.a * u.y)
        return (v1, v2)

    @property
    def asymptotes(self) -> tuple[Line2D, Line2D]:
        """The two asymptotic lines intersecting at center."""
        c_pt = self.center
        u = self.axis_direction
        v = self.conjugate_direction
        a, b = self.a, self.b

        dir1 = Vector2D(a * u.x + b * v.x, a * u.y + b * v.y).normalized()
        dir2 = Vector2D(a * u.x - b * v.x, a * u.y - b * v.y).normalized()
        assert dir1 is not None and dir2 is not None

        # Line from point and direction: -dy*x + dx*y + c = 0
        l1 = Line2D(-dir1.y, dir1.x, dir1.y * c_pt.x - dir1.x * c_pt.y)
        l2 = Line2D(-dir2.y, dir2.x, dir2.y * c_pt.x - dir2.x * c_pt.y)
        return (l1, l2)

    def point_at_param(self, t: float, branch: int = 1) -> Point2D:
        """Evaluate a point on branch 1 (+cosh, focus2 side) or branch 2 (-cosh, focus1 side)."""
        sign = 1.0 if branch == 1 else -1.0
        cosh_t = math.cosh(t)
        sinh_t = math.sinh(t)
        c_pt = self.center
        u = self.axis_direction
        v = self.conjugate_direction
        x = c_pt.x + sign * self.a * cosh_t * u.x + self.b * sinh_t * v.x
        y = c_pt.y + sign * self.a * cosh_t * u.y + self.b * sinh_t * v.y
        return Point2D(x, y)

    def distance_to(self, point: Point2D) -> float:
        """Orthogonal distance metric: ||d(P, F1) - d(P, F2)| - 2a| / 2."""
        d1 = point.distance_to(self.focus1)
        d2 = point.distance_to(self.focus2)
        return abs(abs(d1 - d2) - 2.0 * self.a) / 2.0

    def sample_branch(
        self, branch: int, t_max: float = 3.0, num_points: int = 60
    ) -> tuple[Point2D, ...]:
        """Sample one hyperbola branch for t in [-t_max, t_max]."""
        if num_points < 2:
            num_points = 2
        step = (2.0 * t_max) / (num_points - 1)
        return tuple(
            self.point_at_param(-t_max + i * step, branch=branch) for i in range(num_points)
        )


type Conic2D = Ellipse2D | Parabola2D | Hyperbola2D
