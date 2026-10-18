"""Snapshot serialization and validation helpers for the PyGeoLab debug bridge."""

from __future__ import annotations

import json
from typing import Any


def serialize_snapshot(snapshot: dict[str, Any]) -> str:
    """Serialize runtime snapshot to a deterministic sorted JSON string."""
    return json.dumps(snapshot, indent=2, sort_keys=True)
