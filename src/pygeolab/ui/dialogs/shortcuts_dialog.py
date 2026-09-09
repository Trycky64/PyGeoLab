"""Non-modal reference window for active application shortcuts."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ShortcutsDialog(QDialog):
    """List unique non-empty shortcuts with their user-facing action text."""

    def __init__(self, actions: Iterable[QAction], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Raccourcis clavier"))
        self.setAccessibleName(self.tr("Liste des raccourcis clavier"))
        rows = sorted(
            (
                (action.text().replace("&", ""), action.shortcut().toString())
                for action in actions
                if not action.shortcut().isEmpty()
            ),
            key=lambda row: row[0].casefold(),
        )
        self.table = QTableWidget(len(rows), 2, self)
        self.table.setHorizontalHeaderLabels([self.tr("Action"), self.tr("Raccourci")])
        self.table.setAccessibleName(self.tr("Raccourcis actifs"))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        for row, (label, shortcut) in enumerate(rows):
            self.table.setItem(row, 0, QTableWidgetItem(label))
            self.table.setItem(row, 1, QTableWidgetItem(shortcut))
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        self.resize(520, 420)
