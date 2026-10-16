"""Unit tests for UI controllers: SelectionCoordinator, ActionRegistry, and ProjectController."""

from PySide6.QtWidgets import QApplication, QWidget

from pygeolab.model.document import Document
from pygeolab.persistence import ProjectSession
from pygeolab.ui.action_registry import ActionRegistry
from pygeolab.ui.preferences import Preferences
from pygeolab.ui.project_controller import ProjectController
from pygeolab.ui.selection_coordinator import SelectionCoordinator


def test_selection_coordinator_dispatches_without_reentrancy(qapp: QApplication) -> None:
    coordinator = SelectionCoordinator()
    canvas_calls: list[frozenset[str]] = []
    algebra_calls: list[frozenset[str]] = []

    def on_canvas(ids: frozenset[str]) -> None:
        canvas_calls.append(ids)

    def on_algebra(ids: frozenset[str]) -> None:
        algebra_calls.append(ids)
        # Attempt re-entrant update from listener
        coordinator.set_selection(frozenset({"obj-reentrant"}), source="algebra")

    coordinator.register_listener("canvas", on_canvas)
    coordinator.register_listener("algebra", on_algebra)

    coordinator.set_selection({"obj-1", "obj-2"}, source="canvas")

    assert coordinator.current_selection == frozenset({"obj-1", "obj-2"})
    # Canvas should not receive its own update
    assert not canvas_calls
    # Algebra should receive the update
    assert len(algebra_calls) == 1
    assert algebra_calls[0] == frozenset({"obj-1", "obj-2"})

    # Clear selection
    coordinator.clear(source="algebra")
    assert coordinator.current_selection == frozenset()
    assert len(canvas_calls) == 1
    assert canvas_calls[0] == frozenset()


def test_action_registry_manages_actions_and_history(qapp: QApplication) -> None:
    parent = QWidget()
    registry = ActionRegistry(parent)

    action1 = registry.create_action("undo", "&Annuler", callback=None)
    action2 = registry.create_action("redo", "&Rétablir", callback=None)

    assert registry.action("undo") is action1
    assert registry.action("redo") is action2
    assert len(registry.all_actions()) == 2

    registry.update_history_state(can_undo=False, can_redo=True)
    assert not action1.isEnabled()
    assert action2.isEnabled()

    registry.update_history_state(can_undo=True, can_redo=False)
    assert action1.isEnabled()
    assert not action2.isEnabled()


def test_project_controller_tracks_session_and_dirty(tmp_path: object, qapp: QApplication) -> None:
    doc = Document("Initial")
    session = ProjectSession(document=doc)
    prefs = Preferences()
    controller = ProjectController(preferences=prefs, session=session)

    assert controller.document.name == "Initial"
    assert not controller.dirty
    assert controller.project_path is None

    controller.new_project()
    assert controller.document.name == "Sans titre"

    controller.dispose()
