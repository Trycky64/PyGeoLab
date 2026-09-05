"""Serialize PyGeoLab documents to the versioned JSON project structure."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject, JsonValue

FORMAT_NAME = "pygeolab"
CURRENT_VERSION = 1


def _plain(value: JsonValue) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def serialize_object(obj: GeoObject) -> dict[str, Any]:
    """Serialize one object definition without derived geometry caches."""
    return {
        "id": obj.id,
        "kind": obj.kind,
        "name": obj.name,
        "dependencies": list(obj.dependencies),
        "params": _plain(obj.params),
        "visible": obj.visible,
        "locked": obj.locked,
        "style": {
            "color": obj.style.color,
            "width": obj.style.width,
            "point_size": obj.style.point_size,
            "line_style": obj.style.line_style,
            "show_label": obj.style.show_label,
            "fill_opacity": obj.style.fill_opacity,
        },
    }


def serialize_document(document: Document) -> dict[str, Any]:
    """Return the canonical version-1 project mapping for a document."""
    return {
        "format": FORMAT_NAME,
        "version": CURRENT_VERSION,
        "document": {
            "name": document.name,
            "metadata": _plain(document.metadata),
            "scene": _plain(document.scene),
            "objects": [serialize_object(obj) for obj in document.objects.values()],
        },
    }
