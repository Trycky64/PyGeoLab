"""Main desktop shell integrating geometry tools, project files, export and preferences."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QToolBar,
    QWidget,
)

from pygeolab import __version__
from pygeolab.commands import ChangeFunctionCommand, Command, CreateObjectCommand
from pygeolab.diagnostics import system_information
from pygeolab.exporting import (
    copy_png_to_clipboard,
    copy_svg_to_clipboard,
    export_png,
    export_svg,
    fitted_viewport,
)
from pygeolab.logging_config import log_directory
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style
from pygeolab.persistence import ProjectSession, RecoveryManager
from pygeolab.rendering.viewport import Viewport
from pygeolab.ui.algebra_panel import AlgebraPanel
from pygeolab.ui.dialogs.export_dialog import ExportDialog
from pygeolab.ui.dialogs.function_dialog import FunctionDialog
from pygeolab.ui.dialogs.preferences_dialog import PreferencesDialog
from pygeolab.ui.dialogs.shortcuts_dialog import ShortcutsDialog
from pygeolab.ui.dialogs.slider_dialog import SliderDialog
from pygeolab.ui.error_handler import operation_error_message
from pygeolab.ui.geometry_view import GeometryView
from pygeolab.ui.numerical_panel import NumericalPanel
from pygeolab.ui.preferences import Preferences
from pygeolab.ui.properties_panel import PropertiesPanel
from pygeolab.ui.recent_files import RecentFiles
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

    def __init__(self, *, offer_recovery: bool = True) -> None:
        super().__init__()
        self._disposed = False
        self.resize(1280, 800)
        self.setAccessibleName(self.tr("Fenêtre principale PyGeoLab"))
        self.preferences = Preferences.load()
        self.recent_files = RecentFiles()
        self.recovery = RecoveryManager()
        self.session = ProjectSession()
        self.document = self.session.document
        self.geometry_view = GeometryView(self.document, self)
        self.geometry_view.setAccessibleName(self.tr("Zone de géométrie dynamique"))
        self.setCentralWidget(self.geometry_view)
        self._build_docks()
        self._build_menus()
        self._build_toolbar()
        self._apply_preferences()
        self._apply_accessibility()
        self.geometry_view.selectionChanged.connect(self._selection_from_canvas)
        self.geometry_view.cursorWorldChanged.connect(self._show_cursor)
        self.geometry_view.interactionChanged.connect(self._update_history_actions)
        self._unsubscribe_dirty = self.document.subscribe(self._document_changed)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._autosave)
        self._configure_autosave()
        self.statusBar().setAccessibleName(self.tr("Barre d'état"))
        self.statusBar().showMessage(self.tr("Prêt"))
        self._update_history_actions()
        self._update_title()
        if offer_recovery:
            self._offer_recovery()

    def _execute_command(self, command: Command) -> None:
        self.geometry_view.history.execute(command)
        self._update_history_actions()

    def _build_docks(self) -> None:
        self.algebra_panel = AlgebraPanel(self.document, self._execute_command, self)
        self.algebra_panel.selectionChanged.connect(self._selection_from_algebra)
        self.algebra_panel.sliderCreationRequested.connect(self._new_slider)
        self.algebra_dock = QDockWidget(self.tr("Algèbre"), self)
        self.algebra_dock.setObjectName("algebraDock")
        self.algebra_dock.setAccessibleName(self.tr("Panneau Algèbre"))
        self.algebra_dock.setWidget(self.algebra_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.algebra_dock)

        self.properties_panel = PropertiesPanel(self.document, self._execute_command, self)
        self.properties_panel.selectionRequested.connect(self._selection_from_properties)
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

        self.numerical_panel = NumericalPanel(self.document, self)
        self.numerical_dock = QDockWidget(self.tr("Analyse numérique"), self)
        self.numerical_dock.setObjectName("numericalDock")
        self.numerical_dock.setAccessibleName(self.tr("Panneau Analyse numérique"))
        self.numerical_dock.setWidget(self.numerical_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.numerical_dock)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu(self.tr("&Fichier"))
        self._add_action(file_menu, "&Nouveau", self._new_project, QKeySequence.StandardKey.New)
        self._add_action(file_menu, "&Ouvrir…", self._open_project, QKeySequence.StandardKey.Open)
        self.recent_menu = file_menu.addMenu(self.tr("Fichiers &récents"))
        self.recent_menu.aboutToShow.connect(self._refresh_recent_menu)
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
        export_menu.addSeparator()
        self._add_action(export_menu, "Copier le viewport en PNG", self._copy_png)
        self._add_action(export_menu, "Copier le viewport en SVG", self._copy_svg)
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
        self.select_all_action = self._add_action(
            edit_menu,
            "Tout &sélectionner",
            self.geometry_view.select_all,
            QKeySequence.StandardKey.SelectAll,
        )
        self.clear_selection_action = self._add_action(
            edit_menu,
            "Effacer la sélection",
            self.geometry_view.clear_selection,
            "Ctrl+Shift+A",
        )
        self.duplicate_action = self._add_action(
            edit_menu,
            "&Dupliquer",
            self.geometry_view.duplicate_selection,
            "Ctrl+D",
        )
        edit_menu.addSeparator()
        self._add_action(edit_menu, "&Préférences…", self._show_preferences)

        objects_menu = self.menuBar().addMenu(self.tr("&Objets"))
        self._add_action(objects_menu, "Nouveau &curseur…", self._new_slider)
        self.new_function_action = self._add_action(
            objects_menu, "Nouvelle &fonction…", self._new_function, "Ctrl+F"
        )
        self.edit_function_action = self._add_action(
            objects_menu, "&Modifier la fonction…", self._edit_function
        )
        objects_menu.addSeparator()
        self._add_action(
            objects_menu,
            "Mesurer la &longueur sélectionnée",
            lambda: self._measure_selected("length"),
        )
        self._add_action(
            objects_menu, "Mesurer l'&aire sélectionnée", lambda: self._measure_selected("area")
        )

        view_menu = self.menuBar().addMenu(self.tr("&Affichage"))
        view_menu.addAction(self.algebra_dock.toggleViewAction())
        view_menu.addAction(self.properties_dock.toggleViewAction())
        view_menu.addAction(self.slider_dock.toggleViewAction())
        view_menu.addAction(self.numerical_dock.toggleViewAction())
        self._add_action(view_menu, "Réinitialiser la vue", self.geometry_view.reset_view, "Home")
        self.snapping_action = self._add_action(
            view_menu,
            "&Magnétisme (maintenir Alt pour suspendre)",
            self._set_snapping_enabled,
            "M",
        )
        self.snapping_action.setCheckable(True)
        self.snapping_action.setChecked(True)
        theme_menu = view_menu.addMenu(self.tr("Thème"))
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        self.theme_actions: dict[str, QAction] = {}
        for mode, label in (("system", "Système"), ("light", "Clair"), ("dark", "Sombre")):
            action = self._add_action(
                theme_menu,
                label,
                lambda _checked=False, value=mode: self._apply_theme(value),
            )
            action.setCheckable(True)
            theme_group.addAction(action)
            self.theme_actions[mode] = action
        function_menu = view_menu.addMenu(self.tr("Fonctions"))
        quality_menu = function_menu.addMenu(self.tr("Qualité du tracé"))
        quality_group = QActionGroup(self)
        quality_group.setExclusive(True)
        self.function_quality_actions: dict[str, QAction] = {}
        for quality, label in (("low", "Basse"), ("medium", "Normale"), ("high", "Haute")):
            action = QAction(self.tr(label), self)
            action.setCheckable(True)
            action.setChecked(quality == "medium")
            action.triggered.connect(
                lambda checked=False, value=quality: self._set_function_quality(value, checked)
            )
            quality_group.addAction(action)
            quality_menu.addAction(action)
            self.function_quality_actions[quality] = action
        self.function_overlay_actions: dict[str, QAction] = {}
        for name, label in (
            ("roots", "Afficher les racines"),
            ("extrema", "Afficher les extrema"),
            ("intersections", "Afficher les intersections"),
            ("derivative", "Afficher la dérivée"),
        ):
            action = QAction(self.tr(label), self)
            action.setCheckable(True)
            action.toggled.connect(
                lambda checked, value=name: self.geometry_view.set_function_overlay(value, checked)
            )
            function_menu.addAction(action)
            self.function_overlay_actions[name] = action

        help_menu = self.menuBar().addMenu(self.tr("&Aide"))
        self._add_action(help_menu, "&Raccourcis clavier…", self._show_shortcuts, "F1")
        self._add_action(help_menu, "Ouvrir le dossier des &logs", self._open_logs)
        self._add_action(help_menu, "Copier les informations &système", self._copy_system_info)
        self._add_action(help_menu, "À &propos de PyGeoLab", self._show_about)

    def _set_function_quality(self, quality: str, checked: bool) -> None:
        if checked:
            self.geometry_view.set_function_sampling_quality(quality)

    def _sync_function_actions(self) -> None:
        quality = self.document.scene.get("function_sampling_quality", "medium")
        if not isinstance(quality, str) or quality not in self.function_quality_actions:
            quality = "medium"
        for name, action in self.function_quality_actions.items():
            blocked = action.blockSignals(True)
            action.setChecked(name == quality)
            action.blockSignals(blocked)
        for name, action in self.function_overlay_actions.items():
            blocked = action.blockSignals(True)
            action.setChecked(self.document.scene.get(f"show_function_{name}", False) is True)
            action.blockSignals(blocked)

    def _add_action(
        self,
        menu: QMenu,
        text: str,
        callback: Callable[..., object],
        shortcut: QKeySequence.StandardKey | str | None = None,
    ) -> QAction:
        action = QAction(self.tr(text), self)
        action.setStatusTip(self.tr(text.replace("&", "")))
        action.setToolTip(self.tr(text.replace("&", "")))
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def _apply_theme(self, mode: str) -> None:
        application = QApplication.instance()
        if isinstance(application, QApplication):
            apply_theme(application, mode)
            self.preferences = replace(self.preferences, theme_mode=mode)
            self.preferences.save()

    def _set_snapping_enabled(self, enabled: bool) -> None:
        self.geometry_view.set_snapping_enabled(enabled)
        self.preferences = replace(self.preferences, snapping_enabled=enabled)
        self.preferences.save()

    def _apply_preferences(self) -> None:
        application = QApplication.instance()
        if isinstance(application, QApplication):
            apply_theme(application, self.preferences.theme_mode)
        self.geometry_view.configure_display(
            grid=self.preferences.show_grid,
            axes=self.preferences.show_axes,
            labels=self.preferences.show_labels,
        )
        self.geometry_view.set_snapping_enabled(self.preferences.snapping_enabled)
        self.geometry_view.interaction.set_snapping_threshold(self.preferences.snap_threshold_px)
        self.document.default_style = Style(
            color=self.preferences.default_color,
            width=self.preferences.default_width,
            point_size=self.preferences.default_point_size,
        )
        blocked = self.snapping_action.blockSignals(True)
        self.snapping_action.setChecked(self.preferences.snapping_enabled)
        self.snapping_action.blockSignals(blocked)
        for mode, action in self.theme_actions.items():
            blocked = action.blockSignals(True)
            action.setChecked(mode == self.preferences.theme_mode)
            action.blockSignals(blocked)

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
            action.setToolTip(label)
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
        self.geometry_view.delete_selection()
        self._update_history_actions()

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

    def _new_function(self) -> None:
        dialog = FunctionDialog(self.document, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            function = dialog.object_definition()
            if function.name in {obj.name for obj in self.document.objects.values()}:
                raise ValueError("Ce nom est déjà utilisé")
            self._execute_command(CreateObjectCommand(self.document, function))
        except ValueError as exc:
            QMessageBox.warning(self, self.tr("Fonction invalide"), str(exc))

    def _edit_function(self) -> None:
        selected = tuple(self.geometry_view.selected_ids)
        if len(selected) != 1 or self.document.get(selected[0]).kind != "function":
            self.statusBar().showMessage(self.tr("Sélectionnez une fonction à modifier"))
            return
        function = self.document.get(selected[0])
        dialog = FunctionDialog(self.document, function, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            name, dependencies, params = dialog.definition()
            if any(
                obj.name == name and obj.id != function.id for obj in self.document.objects.values()
            ):
                raise ValueError("Ce nom est déjà utilisé")
            self._execute_command(
                ChangeFunctionCommand(self.document, function.id, name, dependencies, params)
            )
        except ValueError as exc:
            QMessageBox.warning(self, self.tr("Fonction invalide"), str(exc))

    def _measure_selected(self, kind: str) -> None:
        selected = tuple(self.geometry_view.selected_ids)
        expected = {"length": {"segment", "vector"}, "area": {"polygon"}}
        if len(selected) != 1 or kind not in expected:
            self.statusBar().showMessage(self.tr("Sélectionnez un objet mesurable"))
            return
        parent = self.document.get(selected[0])
        if parent.kind not in expected[kind]:
            self.statusBar().showMessage(self.tr("La sélection ne convient pas à cette mesure"))
            return
        prefix = "L" if kind == "length" else "Aire"
        measurement = GeoObject(kind, self.document.unique_name(prefix), (parent.id,))
        self._execute_command(CreateObjectCommand(self.document, measurement))

    def _new_project(self) -> None:
        if not self._confirm_discard_changes():
            return
        self.session.new()
        self._discard_recovery()
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
        self._open_path(path)

    def _open_path(self, path: str) -> bool:
        try:
            self.session.open(path)
        except ValueError as exc:
            self._report_operation_error(
                self.tr("Ouverture impossible"),
                self.tr("Le projet n'a pas pu être ouvert. Le document courant a été conservé."),
                exc,
                path,
            )
            return False
        self._discard_recovery()
        self.recent_files.add(path)
        self._adopt_session_document()
        LOGGER.info("Projet ouvert: %s", path)
        return True

    def _open_recent(self, path: str) -> None:
        if self._confirm_discard_changes():
            self._open_path(path)

    def _refresh_recent_menu(self) -> None:
        self.recent_menu.clear()
        paths = self.recent_files.paths()
        for path in paths:
            action = self.recent_menu.addAction(str(path))
            action.triggered.connect(
                lambda _checked=False, value=str(path): self._open_recent(value)
            )
        if paths:
            self.recent_menu.addSeparator()
        clear = self.recent_menu.addAction(self.tr("Effacer les fichiers récents"))
        clear.setEnabled(bool(paths))
        clear.triggered.connect(self.recent_files.clear)

    def _save_project(self) -> bool:
        if self.session.path is None:
            return self._save_project_as()
        try:
            path = self.session.save()
        except ValueError as exc:
            self._report_operation_error(
                self.tr("Enregistrement impossible"),
                self.tr("Le projet n'a pas pu être enregistré."),
                exc,
                str(self.session.path) if self.session.path else None,
            )
            return False
        LOGGER.info("Projet enregistré: %s", path)
        self.recent_files.add(path)
        self._discard_recovery()
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
            self._report_operation_error(
                self.tr("Enregistrement impossible"),
                self.tr("Le projet n'a pas pu être enregistré."),
                exc,
                path,
            )
            return False
        LOGGER.info("Projet enregistré: %s", saved)
        self.recent_files.add(saved)
        self._discard_recovery()
        self._update_title()
        return True

    def _export_png(self) -> None:
        self._export("png")

    def _export_svg(self) -> None:
        self._export("svg")

    def _export(self, format_name: str) -> None:
        extension = format_name.lower()
        current = self.geometry_view.viewport
        options_dialog = ExportDialog(
            current.width,
            current.height,
            self.preferences.export_scale,
            self.preferences.transparent_export,
            bool(self.geometry_view.selected_ids),
            self,
        )
        if options_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        options = options_dialog.options()
        suggested = f"{self.document.name}.{extension}"
        filter_text = "PNG (*.png)" if extension == "png" else "SVG (*.svg)"
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Exporter"), suggested, filter_text)
        if not path:
            return
        try:
            object_ids = self.geometry_view.selected_ids if options.area == "selection" else None
            if options.area in {"document", "selection"}:
                viewport = fitted_viewport(
                    self.document,
                    options.width,
                    options.height,
                    object_ids,
                )
            else:
                viewport = Viewport(
                    current.center,
                    current.scale,
                    options.width,
                    options.height,
                )
            if extension == "png":
                target = export_png(
                    path,
                    self.document,
                    viewport,
                    self.palette(),
                    scale=options.scale,
                    transparent=options.transparent,
                    object_ids=object_ids,
                )
            else:
                target = export_svg(
                    path,
                    self.document,
                    viewport,
                    self.palette(),
                    scale=options.scale,
                    transparent=options.transparent,
                    object_ids=object_ids,
                )
        except (OSError, ValueError) as exc:
            self._report_operation_error(
                self.tr("Export impossible"),
                self.tr(f"L'export {extension.upper()} n'a pas pu être créé."),
                exc,
                path,
            )
            return
        LOGGER.info("Export %s: %s", extension.upper(), target)
        self.statusBar().showMessage(self.tr(f"Exporté vers {target}"), 5000)

    def _copy_png(self) -> None:
        application = QApplication.instance()
        if isinstance(application, QApplication):
            try:
                copy_png_to_clipboard(
                    application, self.document, self.geometry_view.viewport, self.palette()
                )
            except (OSError, ValueError, RuntimeError) as exc:
                self._report_operation_error(
                    self.tr("Copie impossible"),
                    self.tr("Le viewport PNG n'a pas pu être copié."),
                    exc,
                )
                return
            self.statusBar().showMessage(self.tr("Viewport PNG copié"), 3000)

    def _copy_svg(self) -> None:
        application = QApplication.instance()
        if isinstance(application, QApplication):
            try:
                copy_svg_to_clipboard(
                    application, self.document, self.geometry_view.viewport, self.palette()
                )
            except (OSError, ValueError, RuntimeError) as exc:
                self._report_operation_error(
                    self.tr("Copie impossible"),
                    self.tr("Le viewport SVG n'a pas pu être copié."),
                    exc,
                )
                return
            self.statusBar().showMessage(self.tr("Viewport SVG copié"), 3000)

    def _show_preferences(self) -> None:
        dialog = PreferencesDialog(self.preferences, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.preferences = dialog.preferences()
        self.preferences.save()
        self._configure_autosave()
        self._apply_preferences()

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
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            self.statusBar().showMessage(self.tr(f"Dossier des logs : {path}"), 8000)

    def _copy_system_info(self) -> None:
        application = QApplication.instance()
        if isinstance(application, QApplication):
            application.clipboard().setText(system_information())
            self.statusBar().showMessage(self.tr("Informations système copiées"), 3000)

    def _report_operation_error(
        self,
        title: str,
        summary: str,
        error: BaseException,
        path: str | None = None,
    ) -> None:
        LOGGER.error(
            "%s | document=%r revision=%d path=%r error=%s",
            summary,
            self.document.name,
            self.document.revision,
            path,
            error,
        )
        QMessageBox.critical(
            self,
            title,
            operation_error_message(summary, error, log_directory() / "pygeolab.log"),
        )
        self.statusBar().showMessage(title, 5000)

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

    def _configure_autosave(self) -> None:
        self._autosave_timer.setInterval(self.preferences.autosave_interval_minutes * 60_000)
        if self.preferences.autosave_enabled:
            self._autosave_timer.start()
        else:
            self._autosave_timer.stop()

    def _autosave(self) -> None:
        if not self.preferences.autosave_enabled or not self.session.dirty:
            return
        try:
            path = self.recovery.write(self.document)
        except ValueError as exc:
            LOGGER.error(
                "Échec autosave | document=%r revision=%d path=%r error=%s",
                self.document.name,
                self.document.revision,
                str(self.recovery.path),
                exc,
            )
            self.statusBar().showMessage(
                self.tr(f"Échec de la sauvegarde automatique : {exc}"), 8000
            )
            return
        LOGGER.info("Récupération automatique enregistrée: %s", path)
        self.statusBar().showMessage(self.tr("Sauvegarde automatique effectuée"), 3000)

    def _offer_recovery(self) -> None:
        if not self.recovery.available:
            return
        answer = QMessageBox.question(
            self,
            self.tr("Récupération disponible"),
            self.tr("Une sauvegarde de récupération a été trouvée. La restaurer ?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Ignore,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Ignore:
            self._discard_recovery()
            return
        try:
            self.session.recover(self.recovery.load())
        except ValueError as exc:
            LOGGER.warning("Récupération illisible | path=%r error=%s", self.recovery.path, exc)
            QMessageBox.warning(
                self,
                self.tr("Récupération impossible"),
                operation_error_message(
                    self.tr("La récupération est illisible et a été ignorée."),
                    exc,
                    log_directory() / "pygeolab.log",
                ),
            )
            self._discard_recovery()
            return
        self._adopt_session_document()
        self.statusBar().showMessage(self.tr("Document de récupération restauré"), 5000)

    def _discard_recovery(self) -> None:
        try:
            self.recovery.discard()
        except ValueError as exc:
            LOGGER.warning("Nettoyage de récupération impossible: %s", exc)

    def _adopt_session_document(self) -> None:
        self._unsubscribe_dirty()
        self.document = self.session.document
        self.geometry_view.set_document(self.document)
        self.algebra_panel.set_document(self.document)
        self.properties_panel.set_document(self.document)
        self.slider_panel.set_document(self.document)
        self.numerical_panel.set_document(self.document)
        self._apply_preferences()
        self._sync_function_actions()
        self._unsubscribe_dirty = self.document.subscribe(self._document_changed)
        self._update_history_actions()
        self._update_title()

    def _selection_from_canvas(self, ids: frozenset[str]) -> None:
        self.algebra_panel.set_selected_ids(ids)
        self.properties_panel.set_selection(ids)
        self._show_selection_status(ids)

    def _selection_from_algebra(self, ids: frozenset[str]) -> None:
        self.geometry_view.set_selected_ids(ids)
        self.properties_panel.set_selection(ids)
        self._show_selection_status(ids)

    def _selection_from_properties(self, ids: frozenset[str]) -> None:
        self.geometry_view.set_selected_ids(ids)
        self.algebra_panel.set_selected_ids(ids)
        self.properties_panel.set_selection(ids)
        self._show_selection_status(ids)

    def _show_selection_status(self, ids: frozenset[str]) -> None:
        if ids:
            self.statusBar().showMessage(self.tr(f"{len(ids)} objet(s) sélectionné(s)"), 3000)
        else:
            self.statusBar().showMessage(self.tr("Sélection effacée"), 2000)

    def _show_shortcuts(self) -> None:
        self._shortcuts_dialog = ShortcutsDialog(self.findChildren(QAction), self)
        self._shortcuts_dialog.show()

    def _apply_accessibility(self) -> None:
        self.setStyleSheet(
            self.styleSheet()
            + "\nQPushButton, QToolButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {"
            " min-height: 28px; }"
            "\nQPushButton:focus, QToolButton:focus, QComboBox:focus, QLineEdit:focus,"
            " QSpinBox:focus, QDoubleSpinBox:focus, QTreeView:focus, QTableView:focus {"
            " border: 2px solid palette(highlight); }"
        )
        for widget in self.findChildren(QWidget):
            if isinstance(widget, (QAbstractButton, QAbstractSpinBox, QComboBox, QLineEdit)):
                widget.setMinimumHeight(max(28, widget.minimumHeight()))
            if widget.focusPolicy() != Qt.FocusPolicy.NoFocus and not widget.accessibleName():
                name = widget.toolTip() or widget.whatsThis() or widget.objectName()
                widget.setAccessibleName(name or widget.metaObject().className())
            if widget.accessibleName() and not widget.accessibleDescription():
                widget.setAccessibleDescription(widget.toolTip() or widget.accessibleName())

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
            self._dispose()
            event.accept()
        else:
            event.ignore()

    def _dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        self._autosave_timer.stop()
        self._unsubscribe_dirty()
        self.geometry_view.dispose()
        self.algebra_panel.dispose()
        self.properties_panel.dispose()
        self.slider_panel.dispose()
        self.numerical_panel.dispose()
