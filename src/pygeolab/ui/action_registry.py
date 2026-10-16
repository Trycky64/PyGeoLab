"""Centralize application QAction creation, metadata, and shortcut registration."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QMenu, QWidget

TOOL_LABELS: dict[str, str] = {
    "select": "Sélection",
    "point": "Point",
    "segment": "Segment",
    "line": "Droite",
    "circle": "Cercle",
    "polygon": "Polygone",
    "midpoint": "Milieu",
    "intersection": "Intersection",
    "parallel": "Parallèle",
    "perpendicular": "Perpendiculaire",
    "ray": "Demi-droite",
    "vector": "Vecteur",
    "perpendicular_bisector": "Médiatrice",
    "angle_bisector": "Bissectrice",
    "projection": "Projection",
    "point_on": "Point sur objet",
    "circle_radius": "Cercle centre-rayon",
    "circumcircle": "Cercle circonscrit",
    "distance": "Distance",
    "angle": "Angle",
    "translate": "Translation",
    "rotate": "Rotation",
    "reflect_point": "Symétrie centrale",
    "reflect_line": "Symétrie axiale",
    "scale": "Homothétie",
}

TOOL_SHORTCUTS: dict[str, str] = {
    "select": "S",
    "point": "P",
    "segment": "G",
    "line": "D",
    "circle": "C",
    "polygon": "Y",
}


class ActionRegistry(QObject):
    """Factory and registry holding all actions available in menus and toolbars."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._parent_widget = parent
        self._actions: dict[str, QAction] = {}
        self.tool_actions: dict[str, QAction] = {}
        self.theme_actions: dict[str, QAction] = {}
        self.function_quality_actions: dict[str, QAction] = {}
        self.function_overlay_actions: dict[str, QAction] = {}

        self.tool_action_group = QActionGroup(parent)
        self.tool_action_group.setExclusive(True)
        self.theme_group = QActionGroup(parent)
        self.theme_group.setExclusive(True)
        self.quality_group = QActionGroup(parent)
        self.quality_group.setExclusive(True)

    def create_action(
        self,
        key: str,
        text: str,
        callback: Callable[..., object] | None = None,
        shortcut: QKeySequence.StandardKey | str | None = None,
        *,
        checkable: bool = False,
        checked: bool = False,
        menu: QMenu | None = None,
    ) -> QAction:
        """Create and register a managed QAction."""
        tr_text = self._parent_widget.tr(text)
        action = QAction(tr_text, self._parent_widget)
        tip = self._parent_widget.tr(text.replace("&", ""))
        action.setStatusTip(tip)
        action.setToolTip(tip)
        if shortcut is not None:
            action.setShortcut(shortcut)
        if checkable:
            action.setCheckable(True)
            action.setChecked(checked)
        if callback is not None:
            action.triggered.connect(callback)
        if menu is not None:
            menu.addAction(action)
        self._actions[key] = action
        return action

    def action(self, key: str) -> QAction:
        """Retrieve a registered action by key."""
        return self._actions[key]

    def all_actions(self) -> list[QAction]:
        """Return all registered actions for shortcuts and accessibility auditing."""
        return list(self._actions.values())

    def register_tool_action(self, name: str, callback: Callable[[str], None]) -> QAction:
        """Create a toggleable tool action integrated into the construction group."""
        raw_label = TOOL_LABELS.get(name, name)
        label = self._parent_widget.tr(raw_label)
        action = QAction(label, self._parent_widget)
        action.setStatusTip(label)
        action.setToolTip(label)
        action.setCheckable(True)
        action.setData(name)
        if name in TOOL_SHORTCUTS:
            action.setShortcut(TOOL_SHORTCUTS[name])
        action.triggered.connect(lambda checked=False, tool=name: callback(tool))
        self.tool_action_group.addAction(action)
        self.tool_actions[name] = action
        self._actions[f"tool.{name}"] = action
        return action

    def register_theme_action(
        self, mode: str, label: str, callback: Callable[[str], None]
    ) -> QAction:
        """Create a toggleable theme selection action."""
        action = self.create_action(
            f"theme.{mode}",
            label,
            lambda _checked=False, val=mode: callback(val),
            checkable=True,
        )
        self.theme_group.addAction(action)
        self.theme_actions[mode] = action
        return action

    def register_function_quality_action(
        self, quality: str, label: str, callback: Callable[[str, bool], None]
    ) -> QAction:
        """Create a toggleable function sampling quality action."""
        action = QAction(self._parent_widget.tr(label), self._parent_widget)
        action.setCheckable(True)
        action.setChecked(quality == "medium")
        action.triggered.connect(lambda checked=False, val=quality: callback(val, checked))
        self.quality_group.addAction(action)
        self.function_quality_actions[quality] = action
        self._actions[f"function_quality.{quality}"] = action
        return action

    def register_function_overlay_action(
        self, name: str, label: str, callback: Callable[[bool], None]
    ) -> QAction:
        """Create a toggleable function mathematical overlay action."""
        action = QAction(self._parent_widget.tr(label), self._parent_widget)
        action.setCheckable(True)
        action.toggled.connect(callback)
        self.function_overlay_actions[name] = action
        self._actions[f"function_overlay.{name}"] = action
        return action

    def update_history_state(self, can_undo: bool, can_redo: bool) -> None:
        """Enable or disable undo/redo actions depending on history state."""
        if "undo" in self._actions:
            self._actions["undo"].setEnabled(can_undo)
        if "redo" in self._actions:
            self._actions["redo"].setEnabled(can_redo)
