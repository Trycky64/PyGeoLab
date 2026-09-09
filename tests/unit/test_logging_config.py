"""Exercise portable logging paths and rotating-file configuration."""

import logging

from pygeolab.diagnostics import build_identifier, system_information
from pygeolab.logging_config import configure_logging


def test_configure_logging_creates_rotating_log(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    path = configure_logging()
    logging.getLogger("pygeolab.test").info("release smoke log")
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "release smoke log" in content
    assert "pid=" in content and "thread=" in content


def test_system_information_contains_build_python_qt_and_os(monkeypatch) -> None:
    monkeypatch.setenv("PYGEOLAB_BUILD_ID", "abcdef0123456789")

    information = system_information()

    assert build_identifier() == "abcdef012345"
    assert all(
        label in information
        for label in ("PyGeoLab:", "Build:", "Python:", "PySide6:", "Qt:", "OS:")
    )
