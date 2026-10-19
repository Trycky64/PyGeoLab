"""Safe inspection and extraction of PyGeoLab application runtime properties."""

from __future__ import annotations

import logging
import math
import os
import time
from typing import Any

from pygeolab import __version__
from pygeolab.model.document import Document
from pygeolab.ui.main_window import MainWindow

LOGGER = logging.getLogger(__name__)

MAX_SELECTED_IDS_LIMIT = 50


class RuntimeInspector:
    """Safely inspects the live MainWindow on the Qt main thread."""

    def __init__(self, window: MainWindow, start_time: float) -> None:
        self.window = window
        self.start_time = start_time
        self._recent_errors: list[dict[str, Any]] = []

    def record_error(self, message: str, level: str = "ERROR") -> None:
        """Record a structured application error in bounded FIFO."""
        if len(self._recent_errors) >= 20:
            self._recent_errors.pop(0)
        self._recent_errors.append(
            {
                "timestamp": time.time(),
                "level": level,
                "message": message[:500],
            }
        )

    def collect_snapshot(self) -> dict[str, Any]:
        """Build an authentic, deterministic snapshot from the live MainWindow state."""
        uptime = round(time.time() - self.start_time, 2)
        pid = os.getpid()

        # 1. Document properties
        doc: Document | None = getattr(self.window, "document", None)
        document_name: str | None = None
        objects_count: int | None = None

        if doc is not None:
            document_name = doc.name
            objects_count = len(doc.objects)

        # 2. Session dirty state
        session = getattr(self.window, "session", None)
        is_dirty: bool | None = None
        if session is not None and hasattr(session, "dirty"):
            try:
                is_dirty = bool(session.dirty)
            except Exception as exc:
                LOGGER.warning("Could not compute session.dirty: %s", exc)
                is_dirty = None

        # 3. Selection coordinator / Geometry view selection
        selected_ids_list: list[str] | None = None
        sel_coord = getattr(self.window, "selection_coordinator", None)
        if sel_coord is not None and hasattr(sel_coord, "selected_ids"):
            raw_ids = sorted(list(sel_coord.selected_ids))
            selected_ids_list = raw_ids[:MAX_SELECTED_IDS_LIMIT]
        elif hasattr(self.window, "geometry_view") and hasattr(
            self.window.geometry_view, "selected_ids"
        ):
            raw_ids = sorted(list(self.window.geometry_view.selected_ids))
            selected_ids_list = raw_ids[:MAX_SELECTED_IDS_LIMIT]

        # 4. Active tool
        active_tool_name: str | None = None
        if (
            hasattr(self.window, "geometry_view")
            and hasattr(self.window.geometry_view, "interaction")
            and hasattr(self.window.geometry_view.interaction, "active_tool_name")
        ):
            active_tool_name = str(self.window.geometry_view.interaction.active_tool_name)

        # 5. Viewport camera
        viewport_info: dict[str, Any] | None = None
        if hasattr(self.window, "geometry_view") and hasattr(self.window.geometry_view, "viewport"):
            vp = self.window.geometry_view.viewport
            if vp is not None:
                viewport_info = {
                    "width": vp.width,
                    "height": vp.height,
                    "scale": round(float(vp.scale), 4),
                    "center": {
                        "x": round(float(vp.center.x), 4),
                        "y": round(float(vp.center.y), 4),
                    },
                }

        # 6. Assemble deterministic snapshot
        return {
            "schema_version": "1.0.0",
            "version": __version__,
            "pid": pid,
            "uptime_s": uptime,
            "connected": True,
            "document": {
                "name": document_name,
                "dirty": is_dirty,
                "objects_count": objects_count,
            },
            "selection": {
                "selected_ids": selected_ids_list,
                "count": len(selected_ids_list) if selected_ids_list is not None else None,
                "truncated": len(raw_ids) > MAX_SELECTED_IDS_LIMIT
                if selected_ids_list is not None
                else False,
            },
            "tool": {
                "active": active_tool_name,
            },
            "viewport": viewport_info,
            "recent_errors": list(self._recent_errors),
        }

    def list_objects(
        self,
        limit: int = 50,
        cursor: str | None = None,
        kind: str | None = None,
    ) -> dict[str, Any]:
        """List geometry objects from document with deterministic pagination.

        Parameters:
            limit: bounded integer between 1 and 100 (default 50).
            cursor: optional opaque pagination cursor (format: 'revision:offset').
            kind: optional filter on GeoObject kind.
        """
        # 1. Parameter normalization & validation
        if not isinstance(limit, int) or limit < 1:
            limit = 50
        elif limit > 100:
            limit = 100

        doc: Document | None = getattr(self.window, "document", None)
        if doc is None:
            return {
                "schema_version": "1.0.0",
                "document_id": "none",
                "document_revision": 0,
                "items": [],
                "returned_count": 0,
                "total_count": 0,
                "next_cursor": None,
                "truncated": False,
            }

        doc_rev = getattr(doc, "revision", 0)
        doc_id = getattr(doc, "name", "document")

        offset = 0
        if cursor is not None:
            if not isinstance(cursor, str):
                from pygeolab.debug.protocol import INVALID_PARAMS, ProtocolError

                raise ProtocolError(INVALID_PARAMS, "Cursor must be a string")
            parts = cursor.split(":")
            if len(parts) != 2:
                from pygeolab.debug.protocol import INVALID_PARAMS, ProtocolError

                raise ProtocolError(INVALID_PARAMS, "Malformed cursor format")
            try:
                cur_rev = int(parts[0])
                offset = int(parts[1])
            except ValueError as exc:
                from pygeolab.debug.protocol import INVALID_PARAMS, ProtocolError

                raise ProtocolError(INVALID_PARAMS, "Malformed cursor format") from exc

            if cur_rev != doc_rev:
                from pygeolab.debug.protocol import DOCUMENT_REVISION_MISMATCH, ProtocolError

                msg = (
                    f"Document revision changed during pagination "
                    f"(expected {cur_rev}, current {doc_rev})"
                )
                raise ProtocolError(
                    DOCUMENT_REVISION_MISMATCH,
                    msg,
                    data={"current_revision": doc_rev},
                )

        if offset < 0:
            offset = 0

        # 2. Gather objects
        all_objects = list(doc.objects.values())
        if kind is not None:
            all_objects = [obj for obj in all_objects if obj.kind == kind]

        total_count = len(all_objects)
        paged_objects = all_objects[offset : offset + limit]
        returned_count = len(paged_objects)
        next_offset = offset + returned_count
        has_more = next_offset < total_count
        next_cursor = f"{doc_rev}:{next_offset}" if has_more else None

        # 3. Retrieve selection set for quick selected flag check
        selected_ids = self._get_selected_ids_set()

        items: list[dict[str, Any]] = []
        for obj in paged_objects:
            items.append(
                {
                    "id": obj.id,
                    "name": obj.name,
                    "kind": obj.kind,
                    "valid": bool(obj.valid),
                    "visible": bool(obj.visible),
                    "selected": obj.id in selected_ids,
                }
            )

        return {
            "schema_version": "1.0.0",
            "document_id": doc_id,
            "document_revision": doc_rev,
            "items": items,
            "returned_count": returned_count,
            "total_count": total_count,
            "next_cursor": next_cursor,
            "truncated": has_more,
        }

    def inspect_object(self, object_id: str) -> dict[str, Any]:
        """Inspect a single geometry object in the current document.

        Raises ProtocolError(OBJECT_NOT_FOUND) if object_id is unknown.
        """
        if not isinstance(object_id, str) or not object_id:
            from pygeolab.debug.protocol import INVALID_PARAMS, ProtocolError

            raise ProtocolError(INVALID_PARAMS, "object_id must be a non-empty string")

        doc: Document | None = getattr(self.window, "document", None)
        if doc is None or object_id not in doc.objects:
            from pygeolab.debug.protocol import OBJECT_NOT_FOUND, ProtocolError

            raise ProtocolError(OBJECT_NOT_FOUND, f"Object '{object_id}' not found")

        obj = doc.objects[object_id]
        selected_ids = self._get_selected_ids_set()

        # Sanitize parameters
        params = _sanitize_json_value(dict(obj.params))

        # Serialize computed geometry
        computed_geo, geo_errors = _serialize_geometry(obj.geometry)

        # Validity determination
        errors: list[str] = []
        warnings: list[str] = []
        if obj.error_state:
            errors.append(str(obj.error_state))
        errors.extend(geo_errors)

        validity = "valid"
        if not obj.valid or errors:
            validity = "invalid"
        elif computed_geo is None:
            validity = "empty"

        return {
            "schema_version": "1.0.0",
            "id": obj.id,
            "name": obj.name,
            "kind": obj.kind,
            "parameters": params if isinstance(params, dict) else {},
            "computed_geometry": computed_geo,
            "validity": validity,
            "visible": bool(obj.visible),
            "selected": obj.id in selected_ids,
            "errors": errors,
            "warnings": warnings,
        }

    def _get_selected_ids_set(self) -> set[str]:
        """Safely extract selected IDs set from MainWindow."""
        sel_coord = getattr(self.window, "selection_coordinator", None)
        if sel_coord is not None and hasattr(sel_coord, "selected_ids"):
            return set(sel_coord.selected_ids)
        if hasattr(self.window, "geometry_view") and hasattr(
            self.window.geometry_view, "selected_ids"
        ):
            return set(self.window.geometry_view.selected_ids)
        return set()


def _sanitize_float(val: float | int) -> float | None:
    """Ensure float is finite, returning None if NaN or Infinite."""
    f_val = float(val)
    if not math.isfinite(f_val):
        return None
    return round(f_val, 6)


def _sanitize_json_value(val: Any) -> Any:
    """Recursively sanitize JSON values converting non-finite floats to None."""
    if val is None or isinstance(val, (bool, str)):
        return val
    if isinstance(val, (int, float)):
        f_val = float(val)
        return f_val if math.isfinite(f_val) else None
    if isinstance(val, (list, tuple)):
        return [_sanitize_json_value(x) for x in val]
    if isinstance(val, dict):
        return {str(k): _sanitize_json_value(v) for k, v in val.items()}
    return None


def _serialize_geometry(geo: Any) -> tuple[dict[str, Any] | None, list[str]]:
    """Safely and explicitly serialize a computed geometry object by its concrete type."""
    if geo is None:
        return None, []

    errors: list[str] = []

    from pygeolab.data.dataset import DatasetObject
    from pygeolab.geometry.conics import Ellipse2D, Hyperbola2D, Parabola2D
    from pygeolab.geometry.locus import Locus2D
    from pygeolab.geometry.primitives import (
        Circle2D,
        Line2D,
        Point2D,
        Polygon2D,
        Ray2D,
        Segment2D,
        Vector2D,
    )
    from pygeolab.math_engine.functions import (
        FunctionObject,
        ParametricFunctionObject,
        PolarFunctionObject,
    )

    if isinstance(geo, Point2D):
        x = _sanitize_float(geo.x)
        y = _sanitize_float(geo.y)
        if x is None or y is None:
            errors.append("Point2D contains non-finite coordinates")
        return {"type": "point", "x": x, "y": y}, errors

    if isinstance(geo, Segment2D):
        sx, sy = _sanitize_float(geo.start.x), _sanitize_float(geo.start.y)
        ex, ey = _sanitize_float(geo.end.x), _sanitize_float(geo.end.y)
        length = _sanitize_float(geo.length)
        if any(v is None for v in (sx, sy, ex, ey, length)):
            errors.append("Segment2D contains non-finite values")
        return {
            "type": "segment",
            "start": {"x": sx, "y": sy},
            "end": {"x": ex, "y": ey},
            "length": length,
        }, errors

    if isinstance(geo, Line2D):
        a, b, c = _sanitize_float(geo.a), _sanitize_float(geo.b), _sanitize_float(geo.c)
        if any(v is None for v in (a, b, c)):
            errors.append("Line2D contains non-finite coefficients")
        return {"type": "line", "a": a, "b": b, "c": c}, errors

    if isinstance(geo, Ray2D):
        sx, sy = _sanitize_float(geo.start.x), _sanitize_float(geo.start.y)
        tx, ty = _sanitize_float(geo.through.x), _sanitize_float(geo.through.y)
        if any(v is None for v in (sx, sy, tx, ty)):
            errors.append("Ray2D contains non-finite coordinates")
        return {
            "type": "ray",
            "start": {"x": sx, "y": sy},
            "through": {"x": tx, "y": ty},
        }, errors

    if isinstance(geo, Circle2D):
        cx, cy = _sanitize_float(geo.center.x), _sanitize_float(geo.center.y)
        r = _sanitize_float(geo.radius)
        if any(v is None for v in (cx, cy, r)):
            errors.append("Circle2D contains non-finite center or radius")
        return {"type": "circle", "center": {"x": cx, "y": cy}, "radius": r}, errors

    if isinstance(geo, Polygon2D):
        verts: list[dict[str, Any]] = []
        for p in geo.vertices:
            vx, vy = _sanitize_float(p.x), _sanitize_float(p.y)
            if vx is None or vy is None:
                errors.append("Polygon2D contains vertex with non-finite coordinates")
            verts.append({"x": vx, "y": vy})
        return {
            "type": "polygon",
            "vertices": verts,
            "vertex_count": len(verts),
        }, errors

    if isinstance(geo, Vector2D):
        vx, vy = _sanitize_float(geo.x), _sanitize_float(geo.y)
        norm = _sanitize_float(geo.norm)
        if any(v is None for v in (vx, vy, norm)):
            errors.append("Vector2D contains non-finite components")
        return {"type": "vector", "x": vx, "y": vy, "norm": norm}, errors

    if isinstance(geo, (int, float)):
        val = _sanitize_float(geo)
        if val is None:
            errors.append("Scalar value is non-finite")
        return {"type": "scalar", "value": val}, errors

    if isinstance(geo, Ellipse2D):
        cx, cy = _sanitize_float(geo.center.x), _sanitize_float(geo.center.y)
        a, b = _sanitize_float(geo.a), _sanitize_float(geo.b)
        ang = _sanitize_float(geo.angle)
        if any(v is None for v in (cx, cy, a, b, ang)):
            errors.append("Ellipse2D contains non-finite values")
        return {
            "type": "ellipse",
            "center": {"x": cx, "y": cy},
            "a": a,
            "b": b,
            "angle": ang,
        }, errors

    if isinstance(geo, Parabola2D):
        fx, fy = _sanitize_float(geo.focus.x), _sanitize_float(geo.focus.y)
        vx, vy = _sanitize_float(geo.vertex.x), _sanitize_float(geo.vertex.y)
        param_val = _sanitize_float(geo.parameter)
        return {
            "type": "parabola",
            "focus": {"x": fx, "y": fy},
            "vertex": {"x": vx, "y": vy},
            "parameter": param_val,
        }, errors

    if isinstance(geo, Hyperbola2D):
        f1x, f1y = _sanitize_float(geo.focus1.x), _sanitize_float(geo.focus1.y)
        f2x, f2y = _sanitize_float(geo.focus2.x), _sanitize_float(geo.focus2.y)
        a = _sanitize_float(geo.a)
        return {
            "type": "hyperbola",
            "focus1": {"x": f1x, "y": f1y},
            "focus2": {"x": f2x, "y": f2y},
            "a": a,
        }, errors

    if isinstance(geo, FunctionObject):
        return {
            "type": "function",
            "name": geo.name,
            "variable": geo.variable,
            "domain": list(geo.domain) if geo.domain is not None else None,
        }, errors

    if isinstance(geo, ParametricFunctionObject):
        return {
            "type": "parametric",
            "name": geo.name,
            "parameter": geo.parameter,
            "t_min": _sanitize_float(geo.t_min),
            "t_max": _sanitize_float(geo.t_max),
        }, errors

    if isinstance(geo, PolarFunctionObject):
        return {
            "type": "polar",
            "name": geo.name,
            "parameter": geo.parameter,
            "theta_min": _sanitize_float(geo.theta_min),
            "theta_max": _sanitize_float(geo.theta_max),
        }, errors

    if isinstance(geo, Locus2D):
        return {
            "type": "locus",
            "target_id": geo.target_id,
            "driver_id": geo.driver_id,
            "segments_count": len(geo.segments),
            "samples": geo.samples,
        }, errors

    if isinstance(geo, DatasetObject):
        return {
            "type": "dataset",
            "name": geo.name,
            "column_names": list(geo.column_names),
            "row_count": len(geo.rows),
            "plot_kind": geo.plot_kind,
        }, errors

    # Unknown or unhandled geometry type
    return {"type": "unknown", "class": type(geo).__name__}, errors
