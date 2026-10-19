"""Safe inspection and extraction of PyGeoLab application runtime properties."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import math
import os
import time
from collections.abc import Mapping
from typing import Any

from pygeolab import __version__
from pygeolab.model.document import Document
from pygeolab.model.objects import KINDS
from pygeolab.ui.main_window import MainWindow

LOGGER = logging.getLogger(__name__)

MAX_SELECTED_IDS_LIMIT = 50
MAX_RECURSION_DEPTH = 5
MAX_COLLECTION_ITEMS = 100
MAX_STRING_LENGTH = 1000
MAX_POLYGON_VERTICES = 100
MAX_LOCUS_SAMPLES = 100
MAX_DATASET_ROWS = 100
MAX_DATASET_COLS = 50
MAX_PARAMS_KEYS = 50


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
            cursor: optional opaque pagination cursor.
            kind: optional filter on GeoObject kind.
        """
        from pygeolab.debug.protocol import (
            DOCUMENT_REVISION_MISMATCH,
            INVALID_PARAMS,
            ProtocolError,
        )

        # 1. Parameter validation
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ProtocolError(
                INVALID_PARAMS,
                f"limit must be an integer between 1 and 100, got {type(limit).__name__} ({limit})",
            )

        if kind is not None:
            if isinstance(kind, bool) or not isinstance(kind, str) or not (1 <= len(kind) <= 64):
                raise ProtocolError(
                    INVALID_PARAMS, "kind must be a non-empty string <= 64 characters"
                )
            if kind not in KINDS:
                raise ProtocolError(INVALID_PARAMS, f"Unknown object kind: '{kind}'")

        doc: Document | None = getattr(self.window, "document", None)
        if doc is None:
            if cursor is not None:
                _decode_cursor(cursor)
                raise ProtocolError(
                    DOCUMENT_REVISION_MISMATCH,
                    "Document is no longer available",
                    data={"current_revision": 0},
                )
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
        state_sig = _compute_state_signature(doc, kind)

        offset = 0
        if cursor is not None:
            c_data = _decode_cursor(cursor)
            if c_data.get("k") != kind:
                msg = (
                    f"Cursor kind filter mismatch (cursor was '{c_data.get('k')}', "
                    f"request is '{kind}')"
                )
                raise ProtocolError(INVALID_PARAMS, msg)
            if c_data.get("dp") != id(doc) or c_data.get("dn") != doc_id:
                raise ProtocolError(
                    DOCUMENT_REVISION_MISMATCH,
                    "Document changed during pagination",
                    data={"current_revision": doc_rev},
                )
            if c_data.get("sig") != state_sig:
                raise ProtocolError(
                    DOCUMENT_REVISION_MISMATCH,
                    "Document state changed during pagination",
                    data={"current_revision": doc_rev},
                )
            offset = c_data["off"]

        # 2. Gather objects sorted canonically by stable identifier (UUID)
        sorted_keys = sorted(doc.objects.keys())
        all_objects = [
            doc.objects[oid] for oid in sorted_keys if kind is None or doc.objects[oid].kind == kind
        ]

        total_count = len(all_objects)
        paged_objects = all_objects[offset : offset + limit]
        returned_count = len(paged_objects)
        next_offset = offset + returned_count
        has_more = next_offset < total_count
        next_cursor = (
            _encode_cursor(doc_id, id(doc), state_sig, kind, next_offset) if has_more else None
        )

        # 3. Retrieve selection set for quick selected flag check
        selected_ids = self._get_selected_ids_set()

        items: list[dict[str, Any]] = []
        for obj in paged_objects:
            items.append(
                {
                    "id": obj.id,
                    "name": obj.name[:MAX_STRING_LENGTH],
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

        Raises:
            ProtocolError(INVALID_PARAMS): if object_id is invalid.
            ProtocolError(OBJECT_NOT_FOUND): if object_id is unknown.
        """
        from pygeolab.debug.protocol import (
            INVALID_PARAMS,
            OBJECT_NOT_FOUND,
            ProtocolError,
        )

        if (
            isinstance(object_id, bool)
            or not isinstance(object_id, str)
            or not (1 <= len(object_id) <= 128)
        ):
            raise ProtocolError(
                INVALID_PARAMS, "object_id must be a string between 1 and 128 characters"
            )

        doc: Document | None = getattr(self.window, "document", None)
        if doc is None or object_id not in doc.objects:
            raise ProtocolError(OBJECT_NOT_FOUND, f"Object '{object_id}' not found")

        obj = doc.objects[object_id]
        selected_ids = self._get_selected_ids_set()

        errors: list[str] = []
        warnings: list[str] = []

        # Sanitize parameters with cycle detection & bounding
        raw_params = dict(obj.params) if hasattr(obj, "params") and obj.params is not None else {}
        params = _sanitize_json_value(raw_params, warnings=warnings)

        # Serialize computed geometry
        computed_geo, geo_errors = _serialize_geometry(obj.geometry, errors=errors)

        # Validity determination
        if obj.error_state:
            errors.append(str(obj.error_state)[:MAX_STRING_LENGTH])

        validity = "valid"
        if not obj.valid or errors:
            validity = "invalid"
        elif computed_geo is None:
            validity = "empty"

        return {
            "schema_version": "1.0.0",
            "id": obj.id,
            "name": obj.name[:MAX_STRING_LENGTH],
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


def _compute_state_signature(doc: Document, kind: str | None) -> str:
    """Compute a bounded, deterministic signature of the document state for list_objects."""
    h = hashlib.sha256()
    doc_rev = getattr(doc, "revision", 0)
    h.update(f"{doc.name}:{doc_rev}:{id(doc)}:{kind or ''};".encode())
    for obj_id in sorted(doc.objects.keys()):
        obj = doc.objects[obj_id]
        if kind is None or obj.kind == kind:
            h.update(f"{obj.id}:{obj.revision};".encode())
    return h.hexdigest()[:16]


def _encode_cursor(
    doc_name: str, doc_ptr: int, state_sig: str, kind: str | None, offset: int
) -> str:
    """Encode an opaque base64url cursor bound to document state and filter."""
    payload = {
        "v": 1,
        "dn": doc_name,
        "dp": doc_ptr,
        "sig": state_sig,
        "k": kind,
        "off": offset,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str) -> dict[str, Any]:
    """Decode and strictly validate an opaque pagination cursor."""
    from pygeolab.debug.protocol import INVALID_PARAMS, ProtocolError

    if isinstance(cursor, bool) or not isinstance(cursor, str):
        raise ProtocolError(INVALID_PARAMS, "Cursor must be a string")
    if not (1 <= len(cursor) <= 256):
        raise ProtocolError(INVALID_PARAMS, "Cursor length must be between 1 and 256 characters")

    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ProtocolError(INVALID_PARAMS, "Malformed cursor format") from exc

    if not isinstance(payload, dict):
        raise ProtocolError(INVALID_PARAMS, "Malformed cursor format (expected JSON object)")

    if payload.get("v") != 1:
        raise ProtocolError(INVALID_PARAMS, "Unsupported cursor version")

    if not isinstance(payload.get("dn"), str) or not payload["dn"]:
        raise ProtocolError(INVALID_PARAMS, "Malformed cursor document identifier")

    if isinstance(payload.get("dp"), bool) or not isinstance(payload.get("dp"), int):
        raise ProtocolError(INVALID_PARAMS, "Malformed cursor document pointer")

    if not isinstance(payload.get("sig"), str) or not (1 <= len(payload["sig"]) <= 64):
        raise ProtocolError(INVALID_PARAMS, "Malformed cursor signature")

    k = payload.get("k")
    if k is not None and (not isinstance(k, str) or not k):
        raise ProtocolError(INVALID_PARAMS, "Malformed cursor kind filter")

    off = payload.get("off")
    if isinstance(off, bool) or not isinstance(off, int) or off < 0:
        raise ProtocolError(INVALID_PARAMS, "Invalid cursor offset")

    return payload


def _sanitize_float(
    val: Any,
    field_name: str = "",
    errors: list[str] | None = None,
) -> float | None:
    """Ensure numeric value is finite float.

    Returns None and records structured notice if NaN or Infinite.
    """
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        if errors is not None:
            errors.append(f"Field '{field_name or 'value'}' is not a numeric value")
        return None
    try:
        f_val = float(val)
    except (ValueError, TypeError, OverflowError):
        if errors is not None:
            errors.append(f"Field '{field_name or 'value'}' cannot be converted to float")
        return None

    if not math.isfinite(f_val):
        if errors is not None:
            errors.append(
                f"Non-finite value '{val}' in '{field_name or 'numeric'}' replaced by null"
            )
        return None
    return round(f_val, 6)


def _sanitize_json_value(
    val: Any,
    depth: int = 0,
    max_depth: int = MAX_RECURSION_DEPTH,
    seen: set[int] | None = None,
    warnings: list[str] | None = None,
) -> Any:
    """Recursively serialize and sanitize arbitrary values with bounds and cycle detection."""
    if val is None:
        return None

    if isinstance(val, bool):
        return val

    if isinstance(val, (int, float)):
        f_val = float(val)
        if not math.isfinite(f_val):
            if warnings is not None:
                warnings.append(f"Non-finite numeric value '{val}' replaced by null in parameters")
            return None
        return val if isinstance(val, int) else round(f_val, 6)

    if isinstance(val, str):
        if len(val) > MAX_STRING_LENGTH:
            if warnings is not None:
                warnings.append(f"String truncated ({len(val)} > {MAX_STRING_LENGTH} chars)")
            return val[:MAX_STRING_LENGTH] + "... [truncated]"
        return val

    if seen is None:
        seen = set()

    obj_id = id(val)
    if obj_id in seen:
        if warnings is not None:
            warnings.append(f"Cyclic reference detected for object of type {type(val).__name__}")
        return {"_cyclic_ref": True, "type": type(val).__name__}

    if depth >= max_depth:
        if warnings is not None:
            warnings.append(f"Max serialization depth ({max_depth}) exceeded")
        return {"_truncated": True, "reason": "max_depth_exceeded"}

    new_seen = seen | {obj_id}

    if isinstance(val, (list, tuple, set, frozenset)):
        items = list(val)
        total_items = len(items)
        truncated = total_items > MAX_COLLECTION_ITEMS
        bounded = items[:MAX_COLLECTION_ITEMS]
        res_list = [
            _sanitize_json_value(x, depth + 1, max_depth, new_seen, warnings) for x in bounded
        ]
        if truncated:
            if warnings is not None:
                warnings.append(
                    f"Collection truncated ({total_items} > {MAX_COLLECTION_ITEMS} items)"
                )
            res_list.append({"_truncated": True, "total_elements": total_items})
        return res_list

    if isinstance(val, (dict, Mapping)):
        items = list(val.items())
        total_keys = len(items)
        truncated = total_keys > MAX_PARAMS_KEYS
        bounded = items[:MAX_PARAMS_KEYS]
        res_dict: dict[str, Any] = {}
        for k, v in bounded:
            k_str = str(k)[:100]
            res_dict[k_str] = _sanitize_json_value(v, depth + 1, max_depth, new_seen, warnings)
        if truncated:
            if warnings is not None:
                warnings.append(
                    f"Dictionary keys truncated ({total_keys} > {MAX_PARAMS_KEYS} keys)"
                )
            res_dict["_truncated"] = True
            res_dict["_total_keys"] = total_keys
        return res_dict

    # Unknown Python object: never call repr() or str() that could leak internals
    if warnings is not None:
        warnings.append(f"Unserializable object of type {type(val).__name__}")
    return {"_unserializable": True, "type": type(val).__name__}


def _serialize_geometry(
    geo: Any, errors: list[str] | None = None
) -> tuple[dict[str, Any] | None, list[str]]:
    """Safely and explicitly serialize a computed geometry object by its concrete type."""
    if errors is None:
        errors = []

    if geo is None:
        return None, errors

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
        x = _sanitize_float(geo.x, "Point2D.x", errors)
        y = _sanitize_float(geo.y, "Point2D.y", errors)
        return {"type": "point", "x": x, "y": y}, errors

    if isinstance(geo, Segment2D):
        sx = _sanitize_float(geo.start.x, "Segment2D.start.x", errors)
        sy = _sanitize_float(geo.start.y, "Segment2D.start.y", errors)
        ex = _sanitize_float(geo.end.x, "Segment2D.end.x", errors)
        ey = _sanitize_float(geo.end.y, "Segment2D.end.y", errors)
        length = _sanitize_float(geo.length, "Segment2D.length", errors)
        return {
            "type": "segment",
            "start": {"x": sx, "y": sy},
            "end": {"x": ex, "y": ey},
            "length": length,
        }, errors

    if isinstance(geo, Line2D):
        a = _sanitize_float(geo.a, "Line2D.a", errors)
        b = _sanitize_float(geo.b, "Line2D.b", errors)
        c = _sanitize_float(geo.c, "Line2D.c", errors)
        return {"type": "line", "a": a, "b": b, "c": c}, errors

    if isinstance(geo, Ray2D):
        sx = _sanitize_float(geo.start.x, "Ray2D.start.x", errors)
        sy = _sanitize_float(geo.start.y, "Ray2D.start.y", errors)
        tx = _sanitize_float(geo.through.x, "Ray2D.through.x", errors)
        ty = _sanitize_float(geo.through.y, "Ray2D.through.y", errors)
        return {
            "type": "ray",
            "start": {"x": sx, "y": sy},
            "through": {"x": tx, "y": ty},
        }, errors

    if isinstance(geo, Circle2D):
        cx = _sanitize_float(geo.center.x, "Circle2D.center.x", errors)
        cy = _sanitize_float(geo.center.y, "Circle2D.center.y", errors)
        r = _sanitize_float(geo.radius, "Circle2D.radius", errors)
        return {"type": "circle", "center": {"x": cx, "y": cy}, "radius": r}, errors

    if isinstance(geo, Polygon2D):
        verts: list[dict[str, Any]] = []
        total_verts = len(geo.vertices)
        for pt in geo.vertices[:MAX_POLYGON_VERTICES]:
            vx = _sanitize_float(pt.x, "Polygon2D.vertex.x", errors)
            vy = _sanitize_float(pt.y, "Polygon2D.vertex.y", errors)
            verts.append({"x": vx, "y": vy})
        poly_res: dict[str, Any] = {
            "type": "polygon",
            "vertices": verts,
            "vertex_count": total_verts,
        }
        if total_verts > MAX_POLYGON_VERTICES:
            poly_res["_truncated"] = True
            poly_res["_returned_vertices"] = len(verts)
        return poly_res, errors

    if isinstance(geo, Vector2D):
        vx = _sanitize_float(geo.x, "Vector2D.x", errors)
        vy = _sanitize_float(geo.y, "Vector2D.y", errors)
        norm = _sanitize_float(geo.norm, "Vector2D.norm", errors)
        return {"type": "vector", "x": vx, "y": vy, "norm": norm}, errors

    if isinstance(geo, (int, float)) and not isinstance(geo, bool):
        val = _sanitize_float(geo, "scalar", errors)
        return {"type": "scalar", "value": val}, errors

    if isinstance(geo, Ellipse2D):
        cx = _sanitize_float(geo.center.x, "Ellipse2D.center.x", errors)
        cy = _sanitize_float(geo.center.y, "Ellipse2D.center.y", errors)
        a = _sanitize_float(geo.a, "Ellipse2D.a", errors)
        b = _sanitize_float(geo.b, "Ellipse2D.b", errors)
        ang = _sanitize_float(geo.angle, "Ellipse2D.angle", errors)
        return {
            "type": "ellipse",
            "center": {"x": cx, "y": cy},
            "a": a,
            "b": b,
            "angle": ang,
        }, errors

    if isinstance(geo, Parabola2D):
        fx = _sanitize_float(geo.focus.x, "Parabola2D.focus.x", errors)
        fy = _sanitize_float(geo.focus.y, "Parabola2D.focus.y", errors)
        vx = _sanitize_float(geo.vertex.x, "Parabola2D.vertex.x", errors)
        vy = _sanitize_float(geo.vertex.y, "Parabola2D.vertex.y", errors)
        param_val = _sanitize_float(geo.parameter, "Parabola2D.parameter", errors)
        return {
            "type": "parabola",
            "focus": {"x": fx, "y": fy},
            "vertex": {"x": vx, "y": vy},
            "parameter": param_val,
        }, errors

    if isinstance(geo, Hyperbola2D):
        f1x = _sanitize_float(geo.focus1.x, "Hyperbola2D.focus1.x", errors)
        f1y = _sanitize_float(geo.focus1.y, "Hyperbola2D.focus1.y", errors)
        f2x = _sanitize_float(geo.focus2.x, "Hyperbola2D.focus2.x", errors)
        f2y = _sanitize_float(geo.focus2.y, "Hyperbola2D.focus2.y", errors)
        a = _sanitize_float(geo.a, "Hyperbola2D.a", errors)
        return {
            "type": "hyperbola",
            "focus1": {"x": f1x, "y": f1y},
            "focus2": {"x": f2x, "y": f2y},
            "a": a,
        }, errors

    if isinstance(geo, FunctionObject):
        return {
            "type": "function",
            "name": str(geo.name)[:100],
            "variable": str(geo.variable)[:50],
            "domain": [_sanitize_float(d, "FunctionObject.domain", errors) for d in geo.domain]
            if geo.domain is not None
            else None,
        }, errors

    if isinstance(geo, ParametricFunctionObject):
        return {
            "type": "parametric",
            "name": str(geo.name)[:100],
            "parameter": str(geo.parameter)[:50],
            "t_min": _sanitize_float(geo.t_min, "ParametricFunctionObject.t_min", errors),
            "t_max": _sanitize_float(geo.t_max, "ParametricFunctionObject.t_max", errors),
        }, errors

    if isinstance(geo, PolarFunctionObject):
        return {
            "type": "polar",
            "name": str(geo.name)[:100],
            "parameter": str(geo.parameter)[:50],
            "theta_min": _sanitize_float(geo.theta_min, "PolarFunctionObject.theta_min", errors),
            "theta_max": _sanitize_float(geo.theta_max, "PolarFunctionObject.theta_max", errors),
        }, errors

    if isinstance(geo, Locus2D):
        sample_points: list[list[float | None]] = []
        total_points = geo.total_points if hasattr(geo, "total_points") else 0
        raw_segments = getattr(geo, "segments", ()) or ()
        for piece in raw_segments:
            for pt in piece:
                if len(sample_points) >= MAX_LOCUS_SAMPLES:
                    break
                sample_points.append(
                    [
                        _sanitize_float(pt.x, "Locus2D.pt.x", errors),
                        _sanitize_float(pt.y, "Locus2D.pt.y", errors),
                    ]
                )
            if len(sample_points) >= MAX_LOCUS_SAMPLES:
                break
        locus_res: dict[str, Any] = {
            "type": "locus",
            "target_id": str(geo.target_id)[:64],
            "driver_id": str(geo.driver_id)[:64],
            "segments_count": len(raw_segments),
            "samples": getattr(geo, "samples", len(sample_points)),
            "sample_points": sample_points,
            "total_points": total_points,
        }
        if total_points > MAX_LOCUS_SAMPLES:
            locus_res["_truncated"] = True
            locus_res["_returned_points"] = len(sample_points)
        return locus_res, errors

    if isinstance(geo, DatasetObject):
        raw_cols = getattr(geo, "column_names", []) or []
        cols = [str(c)[:100] for c in raw_cols[:MAX_DATASET_COLS]]
        dataset_res: dict[str, Any] = {
            "type": "dataset",
            "name": str(geo.name)[:MAX_STRING_LENGTH],
            "column_names": cols,
            "row_count": len(getattr(geo, "rows", [])) if hasattr(geo, "rows") else 0,
            "plot_kind": str(geo.plot_kind)[:50] if getattr(geo, "plot_kind", None) else None,
        }
        if len(raw_cols) > MAX_DATASET_COLS:
            dataset_res["_truncated"] = True
            dataset_res["_returned_columns"] = len(cols)
        return dataset_res, errors

    # Unknown or unhandled geometry type: never call repr() or str()
    return {"type": "unknown", "class": type(geo).__name__}, errors
