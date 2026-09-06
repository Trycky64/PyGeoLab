"""Main desktop shell integrating geometry tools, project files, export and preferences."""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QToolBar,
)

from pygeolab import __version__
from pygeolab.commands import Command, CreateObjectCommand, DeleteObjectCommand
from pygeolab.exporting import export_png, export_svg
from pygeolab.logging_config import log_directory
from pygeolab.persistence import ProjectSession
from pygeolab.ui.algebra_panel import AlgebraPanel
from pygeolab.ui.dialogs.preferences_dialog import PreferencesDialog
from pygeolab.ui.dialogs.slider_dialog import SliderDialog
from pygeolab.ui.geometry_view import GeometryView
from pygeolab.ui.preferences import Preferences
from pygeolab.ui.properties_panel import PropertiesPanel
from pygeolab.ui.slider_panel import SliderPanel
from pygeolab.ui.theme import apply_theme

LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Own desktop layout and route actions to domain, history and persistence services."""

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
        self.setAccessibleName(self.tr("Fenêtre principale PyGeoLab"))
        self.preferences = Preferences.load()
        self.session = ProjectSession()
        self.document = self.session.document
        self.geometry_view = GeometryView(self.document, self)
        self.geometry_view.setAccessibleName(self.tr("Zone de géométrie dynamique"))
        self.setCentralWidget(self.geometry_view)
        self._build_docks()
        self._build_menus()
        self._build_toolbar()
        self.geometry_view.selectionChanged.connect(self._selection_from_canvas)
        self.geometry_view.cursorWorldChanged.connect(self._show_cursor)
        self._unsubscribe_dirty = self.document.subscribe(self._document_changed)
        self.statusBar().setAccessibleName(self.tr("Barre d'état"))
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
        self.algebra_dock.setAccessibleName(self.tr("Panneau Algèbre"))
        self.algebra_dock.setWidget(self.algebra_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.algebra_dock)

        self.properties_panel = PropertiesPanel(self.document, self._execute_command, self)
        self.properties_dock = QDockWidget(self.tr("Propriétés"), self)
        self.properties_dock.setObjectName("propertiesDock")
        self.properties_dock.setAccessibleName(self.tr("Panneau Propriétés"))
        self.properties_dock.setWidget(self.properties_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.properties_dock)

        self.slider_panel = SliderPanel(self.document, self._execute_command, self)
        self.slider_dock = QDockWidget(self.tr("Curseurs"), self)
        self.slider_dock.setObjectName("sliderDock")
        self.slider_dock.setAccessibleName(self.tr("Panneau Curseurs"))
        self.slider_dock.setWidget(self.slider_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.slider_dock)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu(self.tr("&Fichier"))
        self._add_action(file_menu, "&Nouveau", self._new_project, QKeySequence.StandardKey.New)
        self._add_action(file_menu, "&Ouvrir…", self._open_project, QKeySequence.StandardKey.Open)
        self.save_action = self._add_action(
            file_menu,
            "&Enregistrer",
            self._save_project,
            QKeySequence.StandardKey.Save,
        )
        self._add_action(
            file_menu,
            "Enregistrer &sous…",
            self._save_project_as,
            QKeySequence.StandardKey.SaveAs,
        )
        export_menu = file_menu.addMenu(self.tr("&Exporter"))
        self._add_action(export_menu, "Image &PNG…", self._export_png)
        self._add_action(export_menu, "Image &SVG…", self._export_svg)
        file_menu.addSeparator()
        self._add_action(file_menu, "&Quitter", self.close, QKeySequence.StandardKey.Quit)

        edit_menu = self.menuBar().addMenu(self.tr("&Édition"))
        self.undo_action = self._add_action(
            edit_menu,
            "&Annuler",
            self._undo,
            QKeySequence.StandardKey.Undo,
        )
        self.redo_action = self._add_action(
            edit_menu,
            "&Rétablir",
            self._redo,
            QKeySequence.StandardKey.Redo,
        )
        self._add_action(
            edit_menu,
            "&Supprimer",
            self._delete_selection,
            QKeySequence.StandardKey.Delete,
        )
        edit_menu.addSeparator()
        self._add_action(edit_menu, "&Préférences…", self._show_preferences)

        objects_menu = self.menuBar().addMenu(self.tr("&Objets"))
        self._add_action(objects_menu, "Nouveau &curseur…", self._new_slider)

        view_menu = self.menuBar().addMenu(self.tr("&Affichage"))
        view_menu.addAction(self.algebra_dock.toggleViewAction())
        view_menu.addAction(self.properties_dock.toggleViewAction())
        view_menu.addAction(self.slider_dock.toggleViewAction())
        self._add_action(view_menu, "Réinitialiser la vue", self.geometry_view.reset_view, "Home")
        theme_menu = view_menu.addMenu(self.tr("Thème"))
        self._add_action(theme_menu, "Clair", lambda: self._apply_theme(False))
        self._add_action(theme_menu, "Sombre", lambda: self._apply_theme(True))

        help_menu = self.menuBar().addMenu(self.tr("&Aide"))
        self._add_action(help_menu, "Ouvrir le dossier des &logs", self._open_logs)
        self._add_action(help_menu, "À &propos de PyGeoLab", self._show_about)

    def _add_action(
        self,
        menu: QMenu,
        text: str,
        callback: Callable[..., object],
        shortcut: QKeySequence.StandardKey | str | None = None,
    ) -> QAction:
        action = QAction(self.tr(text), self)
        action.setStatusTip(self.tr(text.replace("&", "")))
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def _apply_theme(self, dark: bool) -> None:
        application = QApplication.instance()
        if isinstance(application, QApplication):
            apply_theme(application, dark)
            self.preferences = Preferences(
                dark,
                self.preferences.export_scale,
                self.preferences.transparent_export,
            )
            self.preferences.save()

    def _build_toolbar(self) -> None:
        self.toolbar = QToolBar(self.tr("Constructions"), self)
        self.toolbar.setObjectName("constructionToolbar")
        self.toolbar.setAccessibleName(self.tr("Outils de construction"))
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
            label = self.tr(self.TOOL_LABELS[name])
            action = QAction(label, self)
            action.setStatusTip(label)
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
        LOGGER.info("Nouveau projet")

    def _open_project(self) -> None:
        if not self._confirm_discard_changes():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Ouvrir un projet"),
            "",
            self.tr("Projet PyGeoLab (*.pgl)"),
        )
        if not path:
            return
        try:
            self.session.open(path)
        except ValueError as exc:
            LOGGER.warning("Ouverture refusée pour %s: %s", path, exc)
            QMessageBox.critical(self, self.tr("Ouverture impossible"), str(exc))
            return
        self._adopt_session_document()
        LOGGER.info("Projet ouvert: %s", path)

    def _save_project(self) -> bool:
        if self.session.path is None:
            return self._save_project_as()
        try:
            path = self.session.save()
        except ValueError as exc:
            LOGGER.error("Échec d'enregistrement: %s", exc)
            QMessageBox.critical(self, self.tr("Enregistrement impossible"), str(exc))
            return False
        LOGGER.info("Projet enregistré: %s", path)
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
            saved = self.session.save(path)
        except ValueError as exc:
            LOGGER.error("Échec d'enregistrement vers %s: %s", path, exc)
            QMessageBox.critical(self, self.tr("Enregistrement impossible"), str(exc))
            return False
        LOGGER.info("Projet enregistré: %s", saved)
        self._update_title()
        return True

    def _export_png(self) -> None:
        self._export("png")

    def _export_svg(self) -> None:
        self._export("svg")

    def _export(self, format_name: str) -> None:
        extension = format_name.lower()
        suggested = f"{self.document.name}.{extension}"
        filter_text = "PNG (*.png)" if extension == "png" else "SVG (*.svg)"
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Exporter"), suggested, filter_text)
        if not path:
            return
        try:
            if extension == "png":
                target = export_png(
                    path,
                    self.document,
                    self.geometry_view.viewport,
                    self.palette(),
                    scale=self.preferences.export_scale,
                    transparent=self.preferences.transparent_export,
                )
            else:
                target = export_svg(
                    path,
                    self.document,
                    self.geometry_view.viewport,
                    self.palette(),
                    scale=self.preferences.export_scale,
                    transparent=self.preferences.transparent_export,
                )
        except (OSError, ValueError) as exc:
            LOGGER.error("Échec export %s: %s", extension.upper(), exc)
            QMessageBox.critical(self, self.tr("Export impossible"), str(exc))
            return
        LOGGER.info("Export %s: %s", extension.upper(), target)
        self.statusBar().showMessage(self.tr(f"Exporté vers {target}"), 5000)

    def _show_preferences(self) -> None:
        dialog = PreferencesDialog(self.preferences, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.preferences = dialog.preferences()
        self.preferences.save()
        application = QApplication.instance()
        if isinstance(application, QApplication):
            apply_theme(application, self.preferences.dark_theme)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            self.tr("À propos de PyGeoLab"),
            self.tr(
                f"<b>PyGeoLab {__version__}</b><br>"
                "Géométrie dynamique et visualisation mathématique.<br><br>"
                "Licence MIT · Python · PySide6"
            ),
        )

    def _open_logs(self) -> None:
        path = log_directory()
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

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
