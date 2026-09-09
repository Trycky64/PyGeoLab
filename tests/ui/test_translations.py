"""Verify French and English runtime interface selection."""

import ast
from pathlib import Path

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from pygeolab.persistence import RecoveryManager
from pygeolab.ui import main_window as main_window_module
from pygeolab.ui.dialogs.preferences_dialog import PreferencesDialog
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.preferences import Preferences
from pygeolab.ui.translations import (
    ENGLISH,
    EnglishTranslator,
    install_application_translator,
    resolved_language,
    translate_message,
)

ROOT = Path(__file__).resolve().parents[2]


def test_language_resolution_uses_english_as_international_fallback() -> None:
    assert resolved_language("fr", QLocale(QLocale.Language.English)) == "fr"
    assert resolved_language("en", QLocale(QLocale.Language.French)) == "en"
    assert resolved_language("system", QLocale(QLocale.Language.French)) == "fr"
    assert resolved_language("system", QLocale(QLocale.Language.German)) == "en"


def test_english_catalog_translates_static_and_dynamic_messages() -> None:
    translator = EnglishTranslator()

    assert translator.translate("MainWindow", "&Fichier") == "&File"
    assert translator.translate("MainWindow", "Sélection") == "Select"
    assert translator.translate("MainWindow", "3 objets sélectionnés") == "3 objects selected"
    assert translator.translate("MainWindow", "Exporté vers diagram.svg") == (
        "Exported to diagram.svg"
    )


def test_english_catalog_covers_every_static_qt_source_string() -> None:
    sources: set[str] = set(MainWindow.TOOL_LABELS.values())
    for path in (ROOT / "src" / "pygeolab" / "ui").rglob("*.py"):
        if path.name == "translations.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "tr"
                and node.args
            ):
                continue
            argument = node.args[0]
            candidates = (
                (argument.body, argument.orelse) if isinstance(argument, ast.IfExp) else (argument,)
            )
            sources.update(
                candidate.value
                for candidate in candidates
                if isinstance(candidate, ast.Constant)
                and isinstance(candidate.value, str)
                and candidate.value
            )

    assert sources <= ENGLISH.keys()


def test_preferences_dialog_can_be_created_in_english(qapp: QApplication, qtbot: QtBot) -> None:
    install_application_translator(qapp, "en")
    try:
        dialog = PreferencesDialog(Preferences(language="en"))
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Preferences"
        assert dialog._language.currentData() == "en"
        assert dialog._theme.itemText(0) == "System"
        assert translate_message("Ce nom est déjà utilisé") == "This name is already in use"
    finally:
        install_application_translator(qapp, "fr")


def test_main_workspace_is_available_in_english(
    qapp: QApplication, qtbot: QtBot, monkeypatch, tmp_path
) -> None:
    preferences = Preferences(language="en")
    monkeypatch.setattr(Preferences, "load", classmethod(lambda cls: preferences))
    monkeypatch.setattr(Preferences, "save", lambda self, settings=None: None)
    monkeypatch.setattr(
        main_window_module, "RecoveryManager", lambda: RecoveryManager(tmp_path / "recovery")
    )
    install_application_translator(qapp, "en")
    try:
        window = MainWindow(offer_recovery=False)
        qtbot.addWidget(window)
        menus = [action.text().replace("&", "") for action in window.menuBar().actions()]

        assert menus == ["File", "Edit", "Objects", "View", "Help"]
        assert window.statusBar().currentMessage() == "Ready"
        assert window.tool_actions["select"].text() == "Select"
        assert window.algebra_panel._search.placeholderText() == "Search…"
    finally:
        install_application_translator(qapp, "fr")
