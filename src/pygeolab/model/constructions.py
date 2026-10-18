"""Evaluate serializable construction recipes against already computed parents.

Normal geometric impossibilities return None. Invalid recipes raise ValueError;
the document turns both cases into recoverable invalid object states.
"""

import math

from pygeolab.data.dataset import DatasetObject
from pygeolab.geometry import (
    Circle2D,
    Ellipse2D,
    Hyperbola2D,
    Line2D,
    Locus2D,
    Parabola2D,
    Point2D,
    Polygon2D,
    Ray2D,
    Segment2D,
    Vector2D,
    sample_locus,
)
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
from pygeolab.math_engine.functions import (
    FunctionObject,
    ParametricFunctionObject,
    PolarFunctionObject,
)
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
        if len(parents) == 1 and isinstance(parents[0].geometry, DatasetObject):
            ds = parents[0].geometry
            mode = params.get("mode", "row")
            if mode == "mean":
                if ds.row_count == 0:
                    return None
                stats_x = ds.descriptive_stats(0)
                stats_y = ds.descriptive_stats(1) if ds.column_count >= 2 else stats_x
                return Point2D(stats_x.mean, stats_y.mean)
            raw_idx = params.get("index", 0)
            row_idx = int(raw_idx) if isinstance(raw_idx, (int, float, str)) else 0
            if 0 <= row_idx < ds.row_count:
                row = ds.data[row_idx]
                x = row[0]
                y = row[1] if len(row) >= 2 else 0.0
                return Point2D(x, y)
            return None
        if (
            len(parents) == 2
            and isinstance(parents[0].geometry, float)
            and isinstance(parents[1].geometry, float)
        ):
            return Point2D(parents[0].geometry, parents[1].geometry)
        return Point2D(number(params, "x"), number(params, "y"))
    if kind == "number":
        return number(params, "value")
    if kind == "length":
        geometry = parents[0].geometry
        if isinstance(geometry, Segment2D):
            return geometry.start.distance_to(geometry.end)
        if isinstance(geometry, Vector2D):
            return geometry.norm
        raise ValueError("Une longueur nécessite un segment ou un vecteur")
    if kind == "area":
        geometry = parents[0].geometry
        if not isinstance(geometry, Polygon2D):
            raise ValueError("Une aire nécessite un polygone")
        vertices = geometry.vertices
        return (
            abs(
                sum(
                    point.x * vertices[(index + 1) % len(vertices)].y
                    - vertices[(index + 1) % len(vertices)].x * point.y
                    for index, point in enumerate(vertices)
                )
            )
            / 2
        )
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
        numeric_parents = {parent.name for parent in parents if isinstance(parent.geometry, float)}
        if len(numeric_parents) != len(parents):
            raise ValueError("Les dépendances d'une fonction doivent être numériques")
        if function.external_dependencies != numeric_parents:
            raise ValueError("Les dépendances de la fonction ne correspondent pas à l'expression")
        return function
    if kind == "parametric":
        x_source = params.get("x_source", params.get("x_expr"))
        y_source = params.get("y_source", params.get("y_expr"))
        parameter = params.get("parameter", "t")
        t_min = params.get("t_min", 0.0)
        t_max = params.get("t_max", 2.0 * math.pi)
        domain_value = params.get("domain")
        if (
            domain_value is not None
            and isinstance(domain_value, (tuple, list))
            and len(domain_value) == 2
        ):
            t_min, t_max = domain_value[0], domain_value[1]
        if (
            not isinstance(x_source, str)
            or not isinstance(y_source, str)
            or not isinstance(parameter, str)
        ):
            raise ValueError("Une courbe paramétrique nécessite x(t), y(t) et un paramètre")
        if (
            isinstance(t_min, bool)
            or isinstance(t_max, bool)
            or not isinstance(t_min, (int, float))
            or not isinstance(t_max, (int, float))
        ):
            raise ValueError("Domaine paramétrique invalide")
        parametric = ParametricFunctionObject.from_source(
            obj.name, parameter, x_source, y_source, float(t_min), float(t_max)
        )
        numeric_parents = {parent.name for parent in parents if isinstance(parent.geometry, float)}
        if len(numeric_parents) != len(parents):
            raise ValueError("Les dépendances d'une courbe paramétrique doivent être numériques")
        if parametric.external_dependencies != numeric_parents:
            raise ValueError(
                "Les dépendances de la courbe paramétrique ne correspondent pas à l'expression"
            )
        return parametric
    if kind == "polar":
        r_source = params.get("r_source", params.get("r_expr", params.get("source")))
        parameter = params.get("parameter", "theta")
        theta_min = params.get("theta_min", 0.0)
        theta_max = params.get("theta_max", 2.0 * math.pi)
        use_degrees = bool(params.get("use_degrees", False))
        domain_value = params.get("domain")
        if (
            domain_value is not None
            and isinstance(domain_value, (tuple, list))
            and len(domain_value) == 2
        ):
            theta_min, theta_max = domain_value[0], domain_value[1]
        if not isinstance(r_source, str) or not isinstance(parameter, str):
            raise ValueError("Une courbe polaire nécessite r(theta) et un paramètre angulaire")
        if (
            isinstance(theta_min, bool)
            or isinstance(theta_max, bool)
            or not isinstance(theta_min, (int, float))
            or not isinstance(theta_max, (int, float))
        ):
            raise ValueError("Domaine angulaire invalide")
        polar = PolarFunctionObject.from_source(
            obj.name,
            parameter,
            r_source,
            float(theta_min),
            float(theta_max),
            use_degrees=use_degrees,
        )
        numeric_parents = {parent.name for parent in parents if isinstance(parent.geometry, float)}
        if len(numeric_parents) != len(parents):
            raise ValueError("Les dépendances d'une courbe polaire doivent être numériques")
        if polar.external_dependencies != numeric_parents:
            raise ValueError(
                "Les dépendances de la courbe polaire ne correspondent pas à l'expression"
            )
        return polar
    if kind == "locus":
        if len(parents) < 2:
            raise ValueError("Un lieu géométrique nécessite une cible et un pilote")
        target_parent, driver_parent = parents[0], parents[1]
        start = float(number(params, "start", 0.0))
        sweep_end = float(number(params, "end", 1.0))
        samples = int(number(params, "samples", 150))
        # When evaluated through document recompute, document provides context via params.
        # If segments are already cached or if context document is passed, sample_locus is used.
        context_doc = params.get("_context_document")
        if (
            context_doc is not None
            and hasattr(context_doc, "objects")
            and hasattr(context_doc, "_graph")
        ):
            return sample_locus(
                context_doc.objects,
                context_doc._graph,
                target_parent.id,
                driver_parent.id,
                start,
                sweep_end,
                samples=samples,
            )
        # Fallback: create Locus2D with empty segments if context document not provided yet
        return Locus2D((), target_parent.id, driver_parent.id, start, sweep_end, samples=samples)
    if kind == "dataset":
        raw_headers = params.get("headers", params.get("column_names"))
        if isinstance(raw_headers, (list, tuple)) and raw_headers:
            col_names = tuple(str(c) for c in raw_headers)
        else:
            col_names = ("x", "y")
        plot_kind = str(params.get("plot_kind", "scatter"))

        if parents:
            # Case A: Parents are Points (e.g. Point2D)
            if all(isinstance(parent_item.geometry, Point2D) for parent_item in parents):
                data_pts: list[tuple[float, ...]] = []
                for parent_item in parents:
                    if isinstance(parent_item.geometry, Point2D):
                        data_pts.append((parent_item.geometry.x, parent_item.geometry.y))
                return DatasetObject(
                    name=obj.name, column_names=col_names, rows=tuple(data_pts), plot_kind=plot_kind
                )

            # Case B: Parent is a Polygon2D
            if len(parents) == 1 and isinstance(parents[0].geometry, Polygon2D):
                poly = parents[0].geometry
                poly_pts = tuple((pt.x, pt.y) for pt in poly.vertices)
                return DatasetObject(
                    name=obj.name, column_names=col_names, rows=poly_pts, plot_kind=plot_kind
                )

            # Case C: Parent is a Locus2D
            if len(parents) == 1 and isinstance(parents[0].geometry, Locus2D):
                locus = parents[0].geometry
                locus_pts: list[tuple[float, ...]] = []
                for piece in locus.segments:
                    for pt in piece:
                        locus_pts.append((pt.x, pt.y))
                return DatasetObject(
                    name=obj.name,
                    column_names=col_names,
                    rows=tuple(locus_pts),
                    plot_kind=plot_kind,
                )

            # Case D: Parents are Numbers / Sliders
            if all(isinstance(parent_item.geometry, float) for parent_item in parents):
                mode = params.get(
                    "mode", "xy" if len(parents) % 2 == 0 and len(parents) >= 2 else "series"
                )
                if mode == "xy" and len(parents) % 2 == 0:
                    xy_rows: list[tuple[float, ...]] = []
                    for i in range(len(parents) // 2):
                        v1 = parents[2 * i].geometry
                        v2 = parents[2 * i + 1].geometry
                        if isinstance(v1, float) and isinstance(v2, float):
                            xy_rows.append((v1, v2))
                    return DatasetObject(
                        name=obj.name,
                        column_names=col_names,
                        rows=tuple(xy_rows),
                        plot_kind=plot_kind,
                    )
                else:
                    s_rows: list[tuple[float, ...]] = []
                    for parent_item in parents:
                        if isinstance(parent_item.geometry, float):
                            s_rows.append((parent_item.geometry,))
                    val_names = col_names if len(col_names) == 1 else ("val",)
                    return DatasetObject(
                        name=obj.name,
                        column_names=val_names,
                        rows=tuple(s_rows),
                        plot_kind=plot_kind,
                    )

            # Case E: Parent is a FunctionObject
            if len(parents) >= 1 and isinstance(parents[0].geometry, FunctionObject):
                fn = parents[0].geometry
                start = float(number(params, "start", 0.0))
                x_end = float(number(params, "end", 10.0))
                count = max(2, int(number(params, "count", 20)))
                step = (x_end - start) / (count - 1)
                var_dict = {
                    parent_item.name: float(parent_item.geometry)
                    for parent_item in parents[1:]
                    if isinstance(parent_item.geometry, float)
                }
                fn_pts: list[tuple[float, ...]] = []
                for i in range(count):
                    xi = start + i * step
                    try:
                        yi = fn.evaluate(xi, var_dict)
                        if math.isfinite(yi):
                            fn_pts.append((xi, yi))
                    except Exception:
                        pass
                fn_names = col_names if len(col_names) == 2 else ("x", "f(x)")
                return DatasetObject(
                    name=obj.name, column_names=fn_names, rows=tuple(fn_pts), plot_kind=plot_kind
                )

        if params and (
            "rows" in params or "data" in params or "series" in params or "plot_kind" in params
        ):
            return DatasetObject.from_dict(params, name=obj.name)
        if isinstance(obj.geometry, DatasetObject):
            return obj.geometry
        return DatasetObject(name=obj.name)
    if kind in {"segment", "line", "ray", "vector", "circle"}:
        if kind == "line" and len(parents) == 1 and isinstance(parents[0].geometry, DatasetObject):
            ds = parents[0].geometry
            if ds.row_count < 2 or ds.column_count < 2:
                return None
            try:
                biv = ds.linear_regression(0, 1)
                slope, intercept = biv.slope, biv.intercept
                return Line2D.from_points(
                    Point2D(0.0, intercept),
                    Point2D(1.0, slope + intercept),
                )
            except Exception:
                return None
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
    if kind == "ellipse":
        f1, f2, p = (_point(parent) for parent in parents)
        return Ellipse2D.from_foci_and_point(f1, f2, p)
    if kind == "ellipse_center":
        center, a_pt = _point(parents[0]), _point(parents[1])
        b_val: Point2D | float = _point(parents[2]) if len(parents) == 3 else number(params, "b")
        return Ellipse2D.from_center_axes(center, a_pt, b_val)
    if kind == "parabola":
        f = _point(parents[0])
        d = _line(parents[1])
        return Parabola2D.from_focus_and_directrix(f, d)
    if kind == "hyperbola":
        f1, f2 = _point(parents[0]), _point(parents[1])
        if len(parents) == 3:
            return Hyperbola2D.from_foci_and_point(f1, f2, _point(parents[2]))
        a_val = number(params, "a")
        return Hyperbola2D.from_foci_and_parameter(f1, f2, a_val)
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
