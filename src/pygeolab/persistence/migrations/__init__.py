"""Sequential migrations for historical PyGeoLab project formats."""

from __future__ import annotations

from typing import Any

from pygeolab.persistence.serializer import CURRENT_VERSION, FORMAT_NAME


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate a supported historical mapping to the current project version."""
    version = data.get("version")
    if version == CURRENT_VERSION:
        return data
    if version == 0:
        migrated = {
            "format": FORMAT_NAME,
            "version": 1,
            "document": {
                "name": data.get("name", "Sans titre"),
                "metadata": data.get("metadata", {}),
                "scene": data.get("scene", {}),
                "objects": data.get("objects", []),
            },
        }
        return migrated
    if isinstance(version, int) and version > CURRENT_VERSION:
        raise ValueError("Version .pgl plus récente que cette application")
    raise ValueError("Version .pgl non prise en charge")
