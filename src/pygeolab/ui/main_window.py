"""Main desktop shell hosting geometry interaction, history and inspectable panels."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QDockWidget, QLabel, QMainWindow, QToolBar, QTreeWidget

from pygeolab.model.document import Document
from pygeolab.ui.geometry_view import GeometryView


class MainWindow(QMainWindow):
    """Own the window layout and route actions to the geometry view controller."""

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
        self.setWindowTitle("PyGeoLab")
        self.resize(1280, 800)
        self.document = Document()
        self.geometry_view = GeometryView(self.document, self)
        self.setCentralWidget(self.geometry_view)
        self._build_docks()
        self._build_menus()
        self._build_toolbar()
        self.statusBar().showMessage(self.tr("Prêt"))

    def _build_docks(self) -> None:
        algebra = QTreeWidget()
        algebra.setHeaderLabels([self.tr("Objet"), self.tr("Valeur")])
        self.algebra_dock = QDockWidget(self.tr("Algèbre"), self)
        self.algebra_dock.setObjectName("algebraDock")
        self.algebra_dock.setWidget(algebra)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.algebra_dock)
        self.properties_dock = QDockWidget(self.tr("Propriétés"), self)
        self.properties_dock.setObjectName("propertiesDock")
        self.properties_dock.setWidget(QLabel(self.tr("Sélectionnez un objet")))
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.properties_dock)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu(self.tr("&Fichier"))
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

        view_menu = self.menuBar().addMenu(self.tr("&Affichage"))
        view_menu.addAction(self.algebra_dock.toggleViewAction())
        view_menu.addAction(self.properties_dock.toggleViewAction())

    def _build_toolbar(self) -> None:
        self.toolbar = QToolBar(self.tr("Constructions"), self)
        self.toolbar.setObjectName("constructionToolbar")
        self.addToolBar(self.toolbar)
        self.tool_action_group = QActionGroup(self)
        self.tool_action_group.setExclusive(True)
        self.tool_actions: dict[str, QAction] = {}
        for name in self.geometry_view.interaction.tool_names:
            action = QAction(self.tr(self.TOOL_LABELS[name]), self)
            action.setCheckable(True)
            action.setData(name)
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

    def _redo(self) -> None:
        self.geometry_view.interaction.redo()
