"""Evaluate serializable construction recipes against already computed parents.

Normal geometric impossibilities return None. Invalid recipes raise ValueError;
the document turns both cases into recoverable invalid object states.
"""

import math

from pygeolab.geometry import Circle2D, Line2D, Point2D, Polygon2D, Ray2D, Segment2D, Vector2D
from pygeolab.geometry.intersections import intersections
from pygeolab.geometry.transforms import (
    angle,
    angle_bisector,
    circumcircle,
    midpoint,
    perpendicular_bisector,
    reflect_line,
    reflect_point,
    rotate,
    scale,
    translate,
)
from pygeolab.math_engine.functions import FunctionObject
from pygeolab.model.objects import Geometry, GeoObject, number


def _point(parent: GeoObject) -> Point2D:
    if not isinstance(parent.geometry, Point2D):
        raise ValueError("Un point est attendu")
    return parent.geometry


def _line(parent: GeoObject) -> Line2D:
    geometry = parent.geometry
    if isinstance(geometry, Line2D):
        return geometry
    if isinstance(geometry, (Segment2D, Ray2D)):
        end = geometry.end if isinstance(geometry, Segment2D) else geometry.through
        line = Line2D.from_points(geometry.start, end)
        if line is not None:
            return line
    raise ValueError("Une droite non dégénérée est attendue")


def evaluate(obj: GeoObject, parents: tuple[GeoObject, ...]) -> Geometry | None:
    """Dispatch a documented construction; inputs are ordered parent objects."""
    kind, params = obj.kind, obj.params
    if kind == "point":
        return Point2D(number(params, "x"), number(params, "y"))
    if kind == "number":
        return number(params, "value")
    if kind == "function":
        source = params.get("source")
        variable = params.get("variable", "x")
        domain_value = params.get("domain")
        if not isinstance(source, str) or not isinstance(variable, str):
            raise ValueError("Une fonction nécessite une expression et une variable")
        domain: tuple[float, float] | None = None
        if domain_value is not None:
            if not isinstance(domain_value, tuple) or len(domain_value) != 2:
                raise ValueError("Domaine de fonction invalide")
            domain_start, domain_end = domain_value
            if (
                isinstance(domain_start, bool)
                or isinstance(domain_end, bool)
                or not isinstance(domain_start, (int, float))
                or not isinstance(domain_end, (int, float))
            ):
                raise ValueError("Domaine de fonction invalide")
            domain = (float(domain_start), float(domain_end))
        function = FunctionObject.from_source(obj.name, variable, source, domain)
        numeric_parents = {
            parent.name
            for parent in parents
            if isinstance(parent.geometry, float)
        }
        if len(numeric_parents) != len(parents):
            raise ValueError("Les dépendances d'une fonction doivent être numériques")
        if function.external_dependencies != numeric_parents:
            raise ValueError("Les dépendances de la fonction ne correspondent pas à l'expression")
        return function
    if kind in {"segment", "line", "ray", "vector", "circle"}:
        a, b = (_point(parent) for parent in parents)
        if kind == "segment":
            return Segment2D(a, b)
        if kind == "line":
            return Line2D.from_points(a, b)
        if kind == "ray":
            return None if a.almost_equals(b) else Ray2D(a, b)
        if kind == "vector":
            return Vector2D.between(a, b)
        return Circle2D(a, a.distance_to(b))
    if kind == "circle_radius":
        radius = parents[1].geometry if len(parents) == 2 else number(params, "radius")
        if not isinstance(radius, float):
            raise ValueError("Le rayon doit être numérique")
        return Circle2D(_point(parents[0]), radius)
    if kind == "circumcircle":
        a, b, c = (_point(parent) for parent in parents)
        return circumcircle(a, b, c)
    if kind == "polygon":
        return Polygon2D(tuple(_point(parent) for parent in parents))
    if kind == "midpoint":
        if len(parents) == 1 and isinstance(parents[0].geometry, Segment2D):
            segment = parents[0].geometry
            return midpoint(segment.start, segment.end)
        a, b = (_point(parent) for parent in parents)
        return midpoint(a, b)
    if kind == "intersection":
        first, second = (parent.geometry for parent in parents)
        accepted = (Line2D, Segment2D, Ray2D, Circle2D)
        if not isinstance(first, accepted) or not isinstance(second, accepted):
            raise ValueError("Deux droites, segments, demi-droites ou cercles sont attendus")
        result = intersections(first, second)
        index = int(number(params, "index", 0))
        return result.points[index] if 0 <= index < len(result.points) else None
    if kind in {"parallel", "perpendicular"}:
        point, line = _point(parents[0]), _line(parents[1])
        return line.parallel(point) if kind == "parallel" else line.perpendicular(point)
    if kind == "perpendicular_bisector":
        a, b = (_point(parent) for parent in parents)
        return perpendicular_bisector(a, b)
    if kind in {"angle_bisector", "angle"}:
        a, vertex, b = (_point(parent) for parent in parents)
        return angle(a, vertex, b) if kind == "angle" else angle_bisector(a, vertex, b)
    if kind == "projection":
        point, target = _point(parents[0]), parents[1].geometry
        if isinstance(target, (Segment2D, Ray2D)):
            return target.closest_point(point)
        return _line(parents[1]).project(point)
    if kind == "distance":
        a = _point(parents[0])
        target_geometry = parents[1].geometry
        return (
            a.distance_to(target_geometry)
            if isinstance(target_geometry, Point2D)
            else _line(parents[1]).distance(a)
        )
    if kind == "point_on":
        target, t = parents[0].geometry, number(params, "t", 0)
        if isinstance(target, Circle2D):
            return Point2D(
                target.center.x + target.radius * math.cos(t),
                target.center.y + target.radius * math.sin(t),
            )
        if isinstance(target, Line2D):
            return translate(target.project(Point2D(0, 0)), target.direction * t)
        if isinstance(target, (Segment2D, Ray2D)):
            end = target.end if isinstance(target, Segment2D) else target.through
            t = max(0, min(1, t)) if isinstance(target, Segment2D) else max(0, t)
            return translate(target.start, Vector2D.between(target.start, end) * t)
        raise ValueError("Un support linéaire ou un cercle est attendu")
    return _transform(obj, parents)


def _transform(obj: GeoObject, parents: tuple[GeoObject, ...]) -> Point2D:
    point = _point(parents[0])
    if obj.kind == "translate":
        vector = parents[1].geometry
        if not isinstance(vector, Vector2D):
            raise ValueError("Un vecteur est attendu")
        return translate(point, vector)
    if obj.kind == "reflect_line":
        return reflect_line(point, _line(parents[1]))
    center = _point(parents[1])
    if obj.kind == "reflect_point":
        return reflect_point(point, center)
    if obj.kind == "rotate":
        return rotate(point, number(obj.params, "angle"), center)
    if obj.kind == "scale":
        return scale(point, number(obj.params, "factor"), center)
    raise ValueError(f"Construction inconnue : {obj.kind}")
