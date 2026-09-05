"""Verify reversible command semantics, stack behavior and drag-friendly history recording."""

from dataclasses import replace

import pytest

from pygeolab.commands import (
    ChangeStyleCommand,
    ChangeVisibilityCommand,
    Command,
    CommandHistory,
    CompositeCommand,
    CreateObjectCommand,
    DeleteObjectCommand,
    MovePointCommand,
    RenameObjectCommand,
)
from pygeolab.geometry import Point2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style


def point(name: str, x: float, y: float) -> GeoObject:
    """Create a free point definition for command tests."""
    return GeoObject("point", name, params={"x": x, "y": y})


def test_create_undo_redo_and_new_command_clears_redo() -> None:
    document = Document()
    history = CommandHistory()
    a = point("A", 0, 0)
    history.execute(CreateObjectCommand(document, a))
    assert a.id in document.objects
    assert history.undo()
    assert a.id not in document.objects
    assert history.redo()
    assert a.id in document.objects
    assert history.undo()
    b = point("B", 1, 0)
    history.execute(CreateObjectCommand(document, b))
    assert not history.can_redo


def test_delete_command_restores_cascade() -> None:
    document = Document()
    a, b = point("A", 0, 0), point("B", 4, 0)
    segment = GeoObject("segment", "s", (a.id, b.id))
    middle = GeoObject("midpoint", "M", (segment.id,))
    document.restore((a, b, segment, middle))
    history = CommandHistory()
    history.execute(DeleteObjectCommand(document, a.id))
    assert set(document.objects) == {b.id}
    history.undo()
    assert set(document.objects) == {a.id, b.id, segment.id, middle.id}
    history.redo()
    assert set(document.objects) == {b.id}


def test_move_rename_style_and_visibility_commands() -> None:
    document = Document()
    a = document.add(point("A", 0, 0))
    history = CommandHistory()
    history.execute(MovePointCommand(document, a.id, Point2D(0, 0), Point2D(3, 2)))
    assert document.get(a.id).geometry == Point2D(3, 2)
    history.execute(RenameObjectCommand(document, a.id, "B"))
    assert document.get(a.id).name == "B"
    style = replace(Style(), width=4.0)
    history.execute(ChangeStyleCommand(document, a.id, style))
    assert document.get(a.id).style.width == 4
    history.execute(ChangeVisibilityCommand(document, a.id, False))
    assert not document.get(a.id).visible
    for _ in range(4):
        assert history.undo()
    restored = document.get(a.id)
    assert restored.geometry == Point2D(0, 0)
    assert restored.name == "A"
    assert restored.style == Style()
    assert restored.visible


def test_record_applied_does_not_reexecute_drag_final_state() -> None:
    document = Document()
    a = document.add(point("A", 0, 0))
    history = CommandHistory()
    document.move_point(a.id, Point2D(5, 6))
    history.record_applied(MovePointCommand(document, a.id, Point2D(0, 0), Point2D(5, 6)))
    assert history.undo_count == 1
    assert document.get(a.id).geometry == Point2D(5, 6)
    history.undo()
    assert document.get(a.id).geometry == Point2D(0, 0)
    history.redo()
    assert document.get(a.id).geometry == Point2D(5, 6)


class _RecordingCommand(Command):
    def __init__(self, events: list[str], name: str, fail: bool = False) -> None:
        self.events, self.name, self.fail = events, name, fail

    def execute(self) -> None:
        self.events.append(f"do:{self.name}")
        if self.fail:
            raise RuntimeError("boom")

    def undo(self) -> None:
        self.events.append(f"undo:{self.name}")


def test_composite_command_order_and_rollback() -> None:
    events: list[str] = []
    command = CompositeCommand((_RecordingCommand(events, "a"), _RecordingCommand(events, "b")))
    command.execute()
    command.undo()
    assert events == ["do:a", "do:b", "undo:b", "undo:a"]

    events.clear()
    failing = CompositeCommand(
        (_RecordingCommand(events, "a"), _RecordingCommand(events, "b", fail=True))
    )
    with pytest.raises(RuntimeError):
        failing.execute()
    assert events == ["do:a", "do:b", "undo:a"]


def test_history_limit_discards_oldest_entries() -> None:
    document = Document()
    history = CommandHistory(limit=2)
    for index in range(3):
        history.execute(CreateObjectCommand(document, point(f"P{index}", index, 0)))
    assert history.undo_count == 2
