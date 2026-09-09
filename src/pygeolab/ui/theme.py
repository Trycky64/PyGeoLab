"""Application-level light and dark palettes kept outside the geometry renderer."""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def apply_theme(application: QApplication, mode: str) -> None:
    """Apply the system, explicit light or explicit dark palette."""
    if mode == "system":
        application.setPalette(QPalette())
        return
    if mode == "light":
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(250, 250, 250))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(242, 242, 242))
        palette.setColor(QPalette.ColorRole.Text, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.Button, QColor(242, 242, 242))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(37, 99, 235))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        application.setPalette(palette)
        return
    if mode != "dark":
        raise ValueError("Thème inconnu")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(37, 37, 38))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.Text, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    application.setPalette(palette)
