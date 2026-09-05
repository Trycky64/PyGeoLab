"""Main desktop shell hosting the geometry canvas and inspectable document panels."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QDockWidget, QLabel, QMainWindow, QToolBar, QTreeWidget

from pygeolab.model.document import Document
from pygeolab.ui.geometry_view import GeometryView


class MainWindow(QMainWindow):
    """Own the window layout and route user actions to application services."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PyGeoLab")
        self.resize(1280, 800)
        self.document = Document()
        self.geometry_view = GeometryView(self.document, self)
        self.setCentralWidget(self.geometry_view)
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
        file_menu = self.menuBar().addMenu(self.tr("&Fichier"))
        quit_action = QAction(self.tr("&Quitter"), self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        view_menu = self.menuBar().addMenu(self.tr("&Affichage"))
        view_menu.addAction(self.algebra_dock.toggleViewAction())
        view_menu.addAction(self.properties_dock.toggleViewAction())
        self.toolbar = QToolBar(self.tr("Constructions"), self)
        self.toolbar.setObjectName("constructionToolbar")
        self.addToolBar(self.toolbar)
        self.statusBar().showMessage(self.tr("Prêt"))
