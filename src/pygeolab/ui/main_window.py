"""Main desktop shell integrating construction tools, panels, history and application UX."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QApplication, QDockWidget, QMainWindow, QToolBar

from pygeolab.commands import Command, DeleteObjectCommand
from pygeolab.model.document import Document
from pygeolab.ui.algebra_panel import AlgebraPanel
from pygeolab.ui.geometry_view import GeometryView
from pygeolab.ui.properties_panel import PropertiesPanel
from pygeolab.ui.theme import apply_theme


class MainWindow(QMainWindow):
    """Own the desktop layout and route actions to document, history and interaction services."""

    TOOL_LABELS = {
        "select": "Sélection", "point": "Point", "segment": "Segment", "line": "Droite",
        "circle": "Cercle", "polygon": "Polygone", "midpoint": "Milieu",
        "intersection": "Intersection", "parallel": "Parallèle", "perpendicular": "Perpendiculaire",
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PyGeoLab")
        self.resize(1280, 800)
        self.document = Document()
        self.geometry_view = GeometryView(self.document, self)
        self.setCentralWidget(self.geometry_view)
        self._build_docks(); self._build_menus(); self._build_toolbar()
        self.geometry_view.selectionChanged.connect(self._selection_from_canvas)
        self.geometry_view.cursorWorldChanged.connect(self._show_cursor)
        self.statusBar().showMessage(self.tr("Prêt"))
        self._update_history_actions()

    def _execute_command(self, command: Command) -> None:
        self.geometry_view.history.execute(command)
        self._update_history_actions()

    def _build_docks(self) -> None:
        self.algebra_panel = AlgebraPanel(self.document, self._execute_command, self)
        self.algebra_panel.selectionChanged.connect(self._selection_from_algebra)
        self.algebra_dock = QDockWidget(self.tr("Algèbre"), self)
        self.algebra_dock.setObjectName("algebraDock"); self.algebra_dock.setWidget(self.algebra_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.algebra_dock)
        self.properties_panel = PropertiesPanel(self.document, self._execute_command, self)
        self.properties_dock = QDockWidget(self.tr("Propriétés"), self)
        self.properties_dock.setObjectName("propertiesDock"); self.properties_dock.setWidget(self.properties_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.properties_dock)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu(self.tr("&Fichier"))
        quit_action = QAction(self.tr("&Quitter"), self); quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close); file_menu.addAction(quit_action)
        edit_menu = self.menuBar().addMenu(self.tr("&Édition"))
        self.undo_action = QAction(self.tr("&Annuler"), self); self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self._undo); edit_menu.addAction(self.undo_action)
        self.redo_action = QAction(self.tr("&Rétablir"), self); self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(self._redo); edit_menu.addAction(self.redo_action)
        delete_action = QAction(self.tr("&Supprimer"), self); delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self._delete_selection); edit_menu.addAction(delete_action)
        view_menu = self.menuBar().addMenu(self.tr("&Affichage"))
        view_menu.addAction(self.algebra_dock.toggleViewAction()); view_menu.addAction(self.properties_dock.toggleViewAction())
        reset = QAction(self.tr("Réinitialiser la vue"), self); reset.setShortcut("Home"); reset.triggered.connect(self.geometry_view.reset_view)
        view_menu.addAction(reset)
        theme_menu = view_menu.addMenu(self.tr("Thème"))
        light = QAction(self.tr("Clair"), self); dark = QAction(self.tr("Sombre"), self)
        light.triggered.connect(lambda: apply_theme(QApplication.instance(), False))
        dark.triggered.connect(lambda: apply_theme(QApplication.instance(), True))
        theme_menu.addActions([light, dark])

    def _build_toolbar(self) -> None:
        self.toolbar = QToolBar(self.tr("Constructions"), self); self.toolbar.setObjectName("constructionToolbar")
        self.addToolBar(self.toolbar); self.tool_action_group = QActionGroup(self); self.tool_action_group.setExclusive(True)
        self.tool_actions: dict[str, QAction] = {}
        shortcuts = {"select": "S", "point": "P", "segment": "G", "line": "D", "circle": "C", "polygon": "Y"}
        for name in self.geometry_view.interaction.tool_names:
            action = QAction(self.tr(self.TOOL_LABELS[name]), self); action.setCheckable(True); action.setData(name)
            if name in shortcuts: action.setShortcut(shortcuts[name])
            action.triggered.connect(lambda checked=False, tool=name: self._activate_tool(tool))
            self.tool_action_group.addAction(action); self.toolbar.addAction(action); self.tool_actions[name] = action
        self.tool_actions["select"].setChecked(True)

    def _activate_tool(self, name: str) -> None:
        self.geometry_view.activate_tool(name); self.statusBar().showMessage(self.tr(self.TOOL_LABELS[name]))

    def _undo(self) -> None:
        self.geometry_view.interaction.undo(); self._update_history_actions()

    def _redo(self) -> None:
        self.geometry_view.interaction.redo(); self._update_history_actions()

    def _delete_selection(self) -> None:
        selected = tuple(self.geometry_view.selected_ids)
        if len(selected) == 1:
            self._execute_command(DeleteObjectCommand(self.document, selected[0]))
            self.geometry_view.set_selected_ids(set())

    def _selection_from_canvas(self, ids: frozenset[str]) -> None:
        self.algebra_panel.set_selected_ids(ids); self.properties_panel.set_selection(ids)

    def _selection_from_algebra(self, ids: frozenset[str]) -> None:
        self.geometry_view.set_selected_ids(ids); self.properties_panel.set_selection(ids)

    def _show_cursor(self, x: float, y: float) -> None:
        tool = self.TOOL_LABELS[self.geometry_view.interaction.active_tool_name]
        zoom = self.geometry_view.viewport.scale
        self.statusBar().showMessage(f"{tool} · x={x:.3f}, y={y:.3f} · zoom {zoom:.1f}px/u")

    def _update_history_actions(self) -> None:
        self.undo_action.setEnabled(self.geometry_view.history.can_undo)
        self.redo_action.setEnabled(self.geometry_view.history.can_redo)
