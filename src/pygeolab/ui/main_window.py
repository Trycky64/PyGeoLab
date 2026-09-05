"""Main desktop shell integrating tools, panels, history, sliders and project files."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QToolBar,
)

from pygeolab.commands import Command, CreateObjectCommand, DeleteObjectCommand
from pygeolab.model.document import Document
from pygeolab.persistence import ProjectSession
from pygeolab.ui.algebra_panel import AlgebraPanel
from pygeolab.ui.dialogs.slider_dialog import SliderDialog
from pygeolab.ui.geometry_view import GeometryView
from pygeolab.ui.properties_panel import PropertiesPanel
from pygeolab.ui.slider_panel import SliderPanel
from pygeolab.ui.theme import apply_theme


class MainWindow(QMainWindow):
    """Own desktop layout and route actions to document, history and persistence services."""

    TOOL_LABELS = {
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
    }

    def __init__(self) -> None:
        super().__init__()
        self.resize(1280, 800)
        self.session = ProjectSession()
        self.document = self.session.document
        self.geometry_view = GeometryView(self.document, self)
        self.setCentralWidget(self.geometry_view)
        self._build_docks()
        self._build_menus()
        self._build_toolbar()
        self.geometry_view.selectionChanged.connect(self._selection_from_canvas)
        self.geometry_view.cursorWorldChanged.connect(self._show_cursor)
        self._unsubscribe_dirty = self.document.subscribe(self._document_changed)
        self.statusBar().showMessage(self.tr("Prêt"))
        self._update_history_actions()
        self._update_title()

    def _execute_command(self, command: Command) -> None:
        self.geometry_view.history.execute(command)
        self._update_history_actions()

    def _build_docks(self) -> None:
        self.algebra_panel = AlgebraPanel(self.document, self._execute_command, self)
        self.algebra_panel.selectionChanged.connect(self._selection_from_algebra)
        self.algebra_dock = QDockWidget(self.tr("Algèbre"), self)
        self.algebra_dock.setObjectName("algebraDock")
        self.algebra_dock.setWidget(self.algebra_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.algebra_dock)

        self.properties_panel = PropertiesPanel(self.document, self._execute_command, self)
        self.properties_dock = QDockWidget(self.tr("Propriétés"), self)
        self.properties_dock.setObjectName("propertiesDock")
        self.properties_dock.setWidget(self.properties_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.properties_dock)

        self.slider_panel = SliderPanel(self.document, self._execute_command, self)
        self.slider_dock = QDockWidget(self.tr("Curseurs"), self)
        self.slider_dock.setObjectName("sliderDock")
        self.slider_dock.setWidget(self.slider_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.slider_dock)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu(self.tr("&Fichier"))
        new_action = QAction(self.tr("&Nouveau"), self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)
        open_action = QAction(self.tr("&Ouvrir…"), self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)
        self.save_action = QAction(self.tr("&Enregistrer"), self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self._save_project)
        file_menu.addAction(self.save_action)
        save_as_action = QAction(self.tr("Enregistrer &sous…"), self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._save_project_as)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        quit_action = QAction(self.tr("&Quitter"), self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        edit_menu = self.menuBar().addMenu(self.tr("&Édition"))
        self.undo_action = QAction(self.tr("&Annuler"), self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self._undo)
        edit_menu.addAction(self.undo_action)
        self.redo_action = QAction(self.tr("&Rétablir"), self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(self._redo)
        edit_menu.addAction(self.redo_action)
        delete_action = QAction(self.tr("&Supprimer"), self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self._delete_selection)
        edit_menu.addAction(delete_action)

        objects_menu = self.menuBar().addMenu(self.tr("&Objets"))
        slider_action = QAction(self.tr("Nouveau &curseur…"), self)
        slider_action.triggered.connect(self._new_slider)
        objects_menu.addAction(slider_action)

        view_menu = self.menuBar().addMenu(self.tr("&Affichage"))
        view_menu.addAction(self.algebra_dock.toggleViewAction())
        view_menu.addAction(self.properties_dock.toggleViewAction())
        view_menu.addAction(self.slider_dock.toggleViewAction())
        reset = QAction(self.tr("Réinitialiser la vue"), self)
        reset.setShortcut("Home")
        reset.triggered.connect(self.geometry_view.reset_view)
        view_menu.addAction(reset)
        theme_menu = view_menu.addMenu(self.tr("Thème"))
        light = QAction(self.tr("Clair"), self)
        dark = QAction(self.tr("Sombre"), self)
        light.triggered.connect(lambda: self._apply_theme(False))
        dark.triggered.connect(lambda: self._apply_theme(True))
        theme_menu.addActions([light, dark])

    def _apply_theme(self, dark: bool) -> None:
        application = QApplication.instance()
        if isinstance(application, QApplication):
            apply_theme(application, dark)

    def _build_toolbar(self) -> None:
        self.toolbar = QToolBar(self.tr("Constructions"), self)
        self.toolbar.setObjectName("constructionToolbar")
        self.addToolBar(self.toolbar)
        self.tool_action_group = QActionGroup(self)
        self.tool_action_group.setExclusive(True)
        self.tool_actions: dict[str, QAction] = {}
        shortcuts = {
            "select": "S",
            "point": "P",
            "segment": "G",
            "line": "D",
            "circle": "C",
            "polygon": "Y",
        }
        for name in self.geometry_view.interaction.tool_names:
            action = QAction(self.tr(self.TOOL_LABELS[name]), self)
            action.setCheckable(True)
            action.setData(name)
            if name in shortcuts:
                action.setShortcut(shortcuts[name])
            action.triggered.connect(lambda checked=False, tool=name: self._activate_tool(tool))
            self.tool_action_group.addAction(action)
            self.toolbar.addAction(action)
            self.tool_actions[name] = action
        self.tool_actions["select"].setChecked(True)

    def _activate_tool(self, name: str) -> None:
        self.geometry_view.activate_tool(name)
        self.statusBar().showMessage(self.tr(self.TOOL_LABELS[name]))

    def _undo(self) -> None:
        self.geometry_view.interaction.undo()
        self._update_history_actions()

    def _redo(self) -> None:
        self.geometry_view.interaction.redo()
        self._update_history_actions()

    def _delete_selection(self) -> None:
        selected = tuple(self.geometry_view.selected_ids)
        if len(selected) == 1:
            self._execute_command(DeleteObjectCommand(self.document, selected[0]))
            self.geometry_view.set_selected_ids(set())

    def _new_slider(self) -> None:
        dialog = SliderDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            variable = dialog.variable()
            if variable.name in {obj.name for obj in self.document.objects.values()}:
                variable = dialog.variable().__class__(
                    variable.kind,
                    self.document.unique_name(variable.name),
                    variable.dependencies,
                    variable.params,
                )
            self._execute_command(CreateObjectCommand(self.document, variable))
        except ValueError as exc:
            QMessageBox.warning(self, self.tr("Curseur invalide"), str(exc))

    def _new_project(self) -> None:
        if not self._confirm_discard_changes():
            return
        self.session.new()
        self._adopt_session_document()

    def _open_project(self) -> None:
        if not self._confirm_discard_changes():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Ouvrir un projet"), "", self.tr("Projet PyGeoLab (*.pgl)")
        )
        if not path:
            return
        try:
            self.session.open(path)
        except ValueError as exc:
            QMessageBox.critical(self, self.tr("Ouverture impossible"), str(exc))
            return
        self._adopt_session_document()

    def _save_project(self) -> bool:
        if self.session.path is None:
            return self._save_project_as()
        try:
            self.session.save()
        except ValueError as exc:
            QMessageBox.critical(self, self.tr("Enregistrement impossible"), str(exc))
            return False
        self._update_title()
        return True

    def _save_project_as(self) -> bool:
        suggested = self.session.path.name if self.session.path else f"{self.document.name}.pgl"
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Enregistrer le projet"),
            suggested,
            self.tr("Projet PyGeoLab (*.pgl)"),
        )
        if not path:
            return False
        try:
            self.session.save(path)
        except ValueError as exc:
            QMessageBox.critical(self, self.tr("Enregistrement impossible"), str(exc))
            return False
        self._update_title()
        return True

    def _confirm_discard_changes(self) -> bool:
        if not self.session.dirty:
            return True
        answer = QMessageBox.question(
            self,
            self.tr("Modifications non enregistrées"),
            self.tr("Enregistrer les modifications avant de continuer ?"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return self._save_project()
        return True

    def _adopt_session_document(self) -> None:
        self._unsubscribe_dirty()
        self.document = self.session.document
        self.geometry_view.set_document(self.document)
        self.algebra_panel.set_document(self.document)
        self.properties_panel.set_document(self.document)
        self.slider_panel.set_document(self.document)
        self._unsubscribe_dirty = self.document.subscribe(self._document_changed)
        self._update_history_actions()
        self._update_title()

    def _selection_from_canvas(self, ids: frozenset[str]) -> None:
        self.algebra_panel.set_selected_ids(ids)
        self.properties_panel.set_selection(ids)

    def _selection_from_algebra(self, ids: frozenset[str]) -> None:
        self.geometry_view.set_selected_ids(ids)
        self.properties_panel.set_selection(ids)

    def _show_cursor(self, x: float, y: float) -> None:
        tool = self.TOOL_LABELS[self.geometry_view.interaction.active_tool_name]
        zoom = self.geometry_view.viewport.scale
        self.statusBar().showMessage(f"{tool} · x={x:.3f}, y={y:.3f} · zoom {zoom:.1f}px/u")

    def _document_changed(self) -> None:
        self._update_title()

    def _update_title(self) -> None:
        name = self.session.path.name if self.session.path else self.document.name
        marker = " *" if self.session.dirty else ""
        self.setWindowTitle(f"{name}{marker} — PyGeoLab")

    def _update_history_actions(self) -> None:
        self.undo_action.setEnabled(self.geometry_view.history.can_undo)
        self.redo_action.setEnabled(self.geometry_view.history.can_redo)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Prompt for unsaved changes before allowing the window to close."""
        if self._confirm_discard_changes():
            event.accept()
        else:
            event.ignore()
