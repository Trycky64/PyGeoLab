"""Exercise portable logging paths and rotating-file configuration."""

import logging

from pygeolab.logging_config import configure_logging


def test_configure_logging_creates_rotating_log(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    path = configure_logging()
    logging.getLogger("pygeolab.test").info("release smoke log")
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert path.exists()
    assert "release smoke log" in path.read_text(encoding="utf-8")
