"""Exercise .pgl round trips, validation, migrations and dirty project sessions."""

import json
from pathlib import Path

import pytest

from pygeolab.geometry import Point2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style
from pygeolab.persistence import ProjectSession, document_from_mapping, load_project, save_project
from pygeolab.persistence.serializer import serialize_document


def populated_document() -> Document:
    """Build a small dependency chain with portable metadata and styles."""
    document = Document("Triangle")
    document.metadata["author"] = "test"
    document.scene["grid"] = True
    a = document.add(
        GeoObject("point", "A", params={"x": 1, "y": 2}, style=Style(color="#112233"))
    )
    b = document.add(GeoObject("point", "B", params={"x": 5, "y": 2}))
    document.add(GeoObject("segment", "AB", (a.id, b.id)))
    return document


def test_round_trip_preserves_definitions_and_recomputes_geometry(tmp_path: Path) -> None:
    original = populated_document()
    path = save_project(original, tmp_path / "triangle")
    assert path.suffix == ".pgl"
    loaded = load_project(path)
    assert loaded.name == original.name
    assert loaded.metadata == original.metadata
    assert loaded.scene == original.scene
    assert tuple(loaded.objects) == tuple(original.objects)
    assert loaded.get(next(iter(loaded.objects))).geometry == Point2D(1, 2)
    raw = json.loads(path.read_text(encoding="utf-8"))
    first = raw["document"]["objects"][0]
    assert "geometry" not in first and "revision" not in first


def test_validation_rejects_wrong_format_missing_dependency_and_bad_uuid() -> None:
    valid = serialize_document(populated_document())
    invalid_format = dict(valid, format="other")
    with pytest.raises(ValueError):
        document_from_mapping(invalid_format)
    missing = serialize_document(populated_document())
    missing["document"]["objects"][2]["dependencies"] = ["00000000-0000-0000-0000-000000000099"]
    with pytest.raises(ValueError):
        document_from_mapping(missing)
    bad_id = serialize_document(populated_document())
    bad_id["document"]["objects"][0]["id"] = "not-a-uuid"
    with pytest.raises(ValueError):
        document_from_mapping(bad_id)


def test_version_zero_migrates_and_future_version_is_rejected() -> None:
    current = serialize_document(populated_document())
    legacy = {
        "version": 0,
        "name": current["document"]["name"],
        "objects": current["document"]["objects"],
    }
    assert document_from_mapping(legacy).name == "Triangle"
    future = dict(current, version=999)
    with pytest.raises(ValueError):
        document_from_mapping(future)


def test_session_tracks_dirty_save_open_and_new(tmp_path: Path) -> None:
    session = ProjectSession()
    assert not session.dirty
    session.document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))
    assert session.dirty
    path = session.save(tmp_path / "session.pgl")
    assert path.exists() and not session.dirty
    session.document.update(next(iter(session.document.objects)), name="B")
    assert session.dirty
    reopened = session.open(path)
    assert not session.dirty and next(iter(reopened.objects.values())).name == "A"
    session.new()
    assert session.path is None and not session.dirty and not session.document.objects
