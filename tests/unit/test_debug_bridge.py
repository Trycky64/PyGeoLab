"""Unit and integration tests for the PyGeoLab debug bridge server and inspector."""

from __future__ import annotations

import contextlib
import json
import os
import socket
import sys
import time
from typing import Any
from unittest.mock import MagicMock

if sys.platform == "win32":
    import msvcrt
else:
    msvcrt: Any = None

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from pygeolab.debug.bridge import DebugBridgeServer
from pygeolab.debug.inspector import RuntimeInspector
from pygeolab.debug.protocol import (
    AUTH_FAILED,
    MAX_MESSAGE_BYTES,
    METHOD_NOT_FOUND,
    PAYLOAD_TOO_LARGE,
    PROTOCOL_MISMATCH,
    PROTOCOL_VERSION,
    ProtocolError,
    RequestEnvelope,
    build_error_response,
    build_response,
)
from pygeolab.geometry import Point2D
from pygeolab.model.document import Document
from pygeolab.rendering.viewport import Viewport
from pygeolab.ui.main_window import MainWindow


class DummyMainWindow:
    """Mock MainWindow implementing the observable interfaces required by RuntimeInspector."""

    def __init__(self) -> None:
        self.document = Document("Test Doc")
        self.session = MagicMock()
        self.session.dirty = False

        self.geometry_view = MagicMock()
        self.geometry_view.viewport = Viewport(
            center=Point2D(1.5, 2.5),
            scale=100.0,
            width=800,
            height=600,
        )
        self.geometry_view.selected_ids = frozenset(["obj_1", "obj_2"])

        self.geometry_view.interaction = MagicMock()
        self.geometry_view.interaction.active_tool_name = "circle"

        self.selection_coordinator = MagicMock()
        self.selection_coordinator.selected_ids = frozenset(["obj_1", "obj_2"])


def test_protocol_envelope_parsing() -> None:
    req_bytes = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 1}).encode()
    req = RequestEnvelope.from_bytes(req_bytes)
    assert req.method == "ping"
    assert req.id == 1
    assert req.params == {}


def test_protocol_envelope_errors() -> None:
    # Payload too large
    with pytest.raises(ProtocolError) as exc_info:
        RequestEnvelope.from_bytes(b"a" * (MAX_MESSAGE_BYTES + 10))
    assert exc_info.value.code == PAYLOAD_TOO_LARGE

    # Malformed JSON
    with pytest.raises(ProtocolError):
        RequestEnvelope.from_bytes(b"invalid-json")

    # Non-dict JSON
    with pytest.raises(ProtocolError):
        RequestEnvelope.from_bytes(b"[1, 2, 3]")

    # Invalid jsonrpc version
    with pytest.raises(ProtocolError):
        RequestEnvelope.from_bytes(b'{"jsonrpc": "1.0", "method": "ping"}')

    # Missing or non-string method
    with pytest.raises(ProtocolError):
        RequestEnvelope.from_bytes(b'{"jsonrpc": "2.0"}')
    with pytest.raises(ProtocolError):
        RequestEnvelope.from_bytes(b'{"jsonrpc": "2.0", "method": 123}')

    # Invalid params type
    with pytest.raises(ProtocolError):
        RequestEnvelope.from_bytes(b'{"jsonrpc": "2.0", "method": "ping", "params": "not-a-dict"}')

    # Invalid id type
    with pytest.raises(ProtocolError):
        RequestEnvelope.from_bytes(b'{"jsonrpc": "2.0", "method": "ping", "id": [1]}')


def test_protocol_response_builders() -> None:
    ok = build_response({"result": "val"}, 42)
    assert ok.endswith(b"\n")
    data = json.loads(ok.decode())
    assert data["result"] == {"result": "val"}
    assert data["id"] == 42

    err = build_error_response(
        ProtocolError(-32600, "Invalid Request", data={"details": "foo"}), 42
    )
    err_data = json.loads(err.decode())
    assert err_data["error"]["code"] == -32600
    assert err_data["error"]["data"] == {"details": "foo"}
    assert err_data["id"] == 42

    generic_err = build_error_response(ValueError("Something bad"), 42)
    gen_data = json.loads(generic_err.decode())
    assert gen_data["error"]["code"] == -32603
    assert "Something bad" in gen_data["error"]["message"]


def test_snapshot_serializer() -> None:
    from pygeolab.debug.snapshot import serialize_snapshot

    sample = {"b": 2, "a": 1}
    serialized = serialize_snapshot(sample)
    assert '"a": 1' in serialized
    assert serialized.startswith("{\n")


def test_runtime_inspector_snapshot_collection(qtbot: QtBot) -> None:
    window = MainWindow(offer_recovery=False)
    qtbot.addWidget(window)
    inspector = RuntimeInspector(window, time.time() - 5.0)

    # Empty document nominal state
    snap = inspector.collect_snapshot()
    assert snap["schema_version"] == "1.0.0"
    assert snap["connected"] is True
    assert snap["pid"] == os.getpid()
    assert snap["uptime_s"] >= 5.0
    assert snap["document"]["objects_count"] == 0
    assert snap["tool"]["active"] == "select"
    assert snap["viewport"] is not None
    assert snap["viewport"]["width"] > 0

    from uuid import uuid4

    from pygeolab.commands import CreateObjectCommand
    from pygeolab.model.objects import GeoObject

    obj_id = str(uuid4())
    obj = GeoObject(kind="point", name="A", id=obj_id, params={"x": 0.0, "y": 0.0})
    window.geometry_view.history.execute(CreateObjectCommand(window.document, obj))
    window.geometry_view.set_selected_ids({obj_id})

    snap2 = inspector.collect_snapshot()
    assert snap2["document"]["objects_count"] == 1
    assert obj_id in snap2["selection"]["selected_ids"]
    assert snap2["document"]["dirty"] is True
    # Reset dirty state so closeEvent does not show a blocking QMessageBox
    window.session._saved_snapshot = window.session._saved_snapshot or {}
    from pygeolab.persistence.serializer import serialize_document

    window.session._saved_snapshot = serialize_document(window.document)
    window.close()


def test_runtime_inspector_error_recording() -> None:
    dummy = DummyMainWindow()
    # Test error buffer overflow (> 20)
    inspector = RuntimeInspector(dummy, time.time())  # type: ignore[arg-type]
    for i in range(25):
        inspector.record_error(f"Error {i}")
    snap = inspector.collect_snapshot()
    assert len(snap["recent_errors"]) == 20
    assert snap["recent_errors"][-1]["message"] == "Error 24"


def test_runtime_inspector_truncated_selection_and_none_attributes() -> None:
    dummy = DummyMainWindow()
    # Truncated selection (> 50)
    dummy.selection_coordinator.selected_ids = frozenset([f"id_{i}" for i in range(60)])
    inspector = RuntimeInspector(dummy, time.time())  # type: ignore[arg-type]
    snap = inspector.collect_snapshot()
    assert snap["selection"]["count"] == 50
    assert snap["selection"]["truncated"] is True

    # Bare window with None/missing attributes
    bare_dummy = MagicMock()
    bare_dummy.document = None
    bare_dummy.session = None
    bare_dummy.selection_coordinator = None
    bare_dummy.geometry_view = None
    bare_inspector = RuntimeInspector(bare_dummy, time.time())
    bare_snap = bare_inspector.collect_snapshot()
    assert bare_snap["document"]["name"] is None
    assert bare_snap["document"]["objects_count"] is None
    assert bare_snap["selection"]["selected_ids"] is None
    assert bare_snap["tool"]["active"] is None
    assert bare_snap["viewport"] is None


class _ClientStreamHelper:
    """Helper to open IPC client stream on Windows or Linux."""

    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint
        self.stream: Any = None
        self._h_pipe: Any = None
        self._sock: Any = None

    def connect(self) -> Any:
        if sys.platform == "win32":
            import _winapi

            for _ in range(50):
                try:
                    h = _winapi.CreateFile(
                        self.endpoint,
                        _winapi.GENERIC_READ | _winapi.GENERIC_WRITE,
                        0,
                        0,
                        _winapi.OPEN_EXISTING,
                        0,
                        0,
                    )
                    self._h_pipe = h
                    fd = msvcrt.open_osfhandle(h, 0)
                    self.stream = open(fd, "r+b", buffering=0)
                    return self.stream
                except OSError:
                    time.sleep(0.05)
            raise TimeoutError(f"Could not connect to Named Pipe {self.endpoint}")
        else:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            for _ in range(50):
                try:
                    sock.connect(self.endpoint)
                    self._sock = sock
                    self.stream = sock.makefile("rwb", buffering=0)
                    return self.stream
                except OSError:
                    time.sleep(0.05)
            raise TimeoutError(f"Could not connect to Unix socket {self.endpoint}")

    def close(self) -> None:
        if self.stream is not None:
            with contextlib.suppress(Exception):
                self.stream.close()


def test_debug_bridge_server_handshake_and_snapshot(qtbot: QtBot) -> None:
    window = MainWindow(offer_recovery=False)
    qtbot.addWidget(window)
    server = DebugBridgeServer(window)
    server.start()
    assert server.info_file_path is not None
    assert server.info_file_path.exists()

    helper = _ClientStreamHelper(server.endpoint_address)
    stream = helper.connect()

    try:
        # 1. Calling runtime_snapshot before handshake must fail
        req_snap = (
            json.dumps({"jsonrpc": "2.0", "method": "runtime_snapshot", "id": 1}).encode() + b"\n"
        )
        stream.write(req_snap)
        err_line = stream.readline()
        err_resp = json.loads(err_line.decode())
        assert err_resp["error"]["code"] == AUTH_FAILED

        # 2. Handshake with invalid token must fail
        bad_hs = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "handshake",
                    "params": {"token": "wrong", "version": PROTOCOL_VERSION},
                    "id": 2,
                }
            ).encode()
            + b"\n"
        )
        stream.write(bad_hs)
        err_line2 = stream.readline()
        err_resp2 = json.loads(err_line2.decode())
        assert err_resp2["error"]["code"] == AUTH_FAILED

        # 3. Handshake with mismatched protocol version must fail
        bad_ver = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "handshake",
                    "params": {"token": server.auth_token, "version": "99.0.0"},
                    "id": 3,
                }
            ).encode()
            + b"\n"
        )
        stream.write(bad_ver)
        err_line3 = stream.readline()
        err_resp3 = json.loads(err_line3.decode())
        assert err_resp3["error"]["code"] == PROTOCOL_MISMATCH

        # 4. Valid Handshake
        valid_hs = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "handshake",
                    "params": {"token": server.auth_token, "version": PROTOCOL_VERSION},
                    "id": 4,
                }
            ).encode()
            + b"\n"
        )
        stream.write(valid_hs)
        hs_line = stream.readline()
        hs_resp = json.loads(hs_line.decode())
        assert hs_resp["result"]["status"] == "authenticated"

        # 5. Successful runtime_snapshot
        stream.write(req_snap)
        # Process events on main thread so dispatcher can execute
        for _ in range(50):
            app = QApplication.instance()
            if app is not None:
                app.processEvents()
            time.sleep(0.01)

        snap_line = stream.readline()
        snap_resp = json.loads(snap_line.decode())
        assert "result" in snap_resp
        snap_data = snap_resp["result"]
        assert snap_data["pid"] == os.getpid()
        assert snap_data["connected"] is True
        assert snap_data["document"]["objects_count"] == 0

        # 6. Ping method test
        stream.write(json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 5}).encode() + b"\n")
        ping_line = stream.readline()
        ping_resp = json.loads(ping_line.decode())
        assert ping_resp["result"]["pong"] is True

        # 7. Unknown method rejected
        stream.write(
            json.dumps({"jsonrpc": "2.0", "method": "non_existent_method", "id": 6}).encode()
            + b"\n"
        )
        unk_line = stream.readline()
        unk_resp = json.loads(unk_line.decode())
        assert unk_resp["error"]["code"] == METHOD_NOT_FOUND

    finally:
        helper.close()
        server.stop()
        assert not server.info_file_path.exists()
