"""Safe inspection and extraction of PyGeoLab application runtime properties."""

from __future__ import annotations

import logging
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
