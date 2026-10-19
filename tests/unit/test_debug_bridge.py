"""Unit and integration tests for the PyGeoLab debug bridge server and inspector."""

from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import sys
import time
from pathlib import Path
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
    SERVER_STOPPING,
    ProtocolError,
    RequestEnvelope,
    build_error_response,
    build_response,
    read_bounded_frame,
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

    generic_err = build_error_response(ValueError("SuperSecretLeak1234"), 42)
    gen_data = json.loads(generic_err.decode())
    assert gen_data["error"]["code"] == -32603
    assert gen_data["error"]["message"] == "Internal server error"
    assert "SuperSecretLeak1234" not in gen_data["error"]["message"]


def test_read_bounded_frame_limits() -> None:
    import io

    # Valid frame
    stream = io.BytesIO(b'{"jsonrpc": "2.0", "method": "ping"}\n')
    frame = read_bounded_frame(stream)
    assert frame == b'{"jsonrpc": "2.0", "method": "ping"}'

    # Incomplete frame (no newline)
    stream_incomplete = io.BytesIO(b'{"jsonrpc": "2.0"')
    with pytest.raises(ProtocolError) as exc_info:
        read_bounded_frame(stream_incomplete)
    assert exc_info.value.code == -32700  # PARSE_ERROR

    # Payload exceeding 1 MB
    huge_payload = b"x" * (MAX_MESSAGE_BYTES + 50) + b"\n"
    stream_huge = io.BytesIO(huge_payload)
    with pytest.raises(ProtocolError) as exc_info:
        read_bounded_frame(stream_huge)
    assert exc_info.value.code == PAYLOAD_TOO_LARGE

    # Empty stream at EOF
    stream_eof = io.BytesIO(b"")
    with pytest.raises(EOFError):
        read_bounded_frame(stream_eof)

    # Response builder payload too large
    huge_data = {"key": "x" * (MAX_MESSAGE_BYTES + 10)}
    with pytest.raises(ProtocolError) as exc_info:
        build_response(huge_data, 1)
    assert exc_info.value.code == PAYLOAD_TOO_LARGE


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
        assert snap_data["document"]["dirty"] is False

        # 6. Real mutation in PyGeoLab and snapshot verification over authentic IPC
        from pygeolab.commands.create import CreateObjectCommand
        from pygeolab.model.objects import GeoObject

        obj = GeoObject(
            kind="point",
            name="P_MUT",
            params={"x": 10.0, "y": 20.0},
            geometry=Point2D(10.0, 20.0),
        )
        cmd = CreateObjectCommand(window.document, obj)
        window._execute_command(cmd)

        req_snap2 = (
            json.dumps({"jsonrpc": "2.0", "method": "runtime_snapshot", "id": 5}).encode() + b"\n"
        )
        stream.write(req_snap2)
        for _ in range(50):
            app = QApplication.instance()
            if app is not None:
                app.processEvents()
            time.sleep(0.01)

        snap_line2 = stream.readline()
        snap_resp2 = json.loads(snap_line2.decode())
        assert "result" in snap_resp2
        snap_data2 = snap_resp2["result"]
        assert snap_data2["document"]["objects_count"] == 1
        assert snap_data2["document"]["dirty"] is True

        # 7. Ping method test
        stream.write(json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 6}).encode() + b"\n")
        ping_line = stream.readline()
        ping_resp = json.loads(ping_line.decode())
        assert ping_resp["result"]["pong"] is True

        # 8. Unknown method rejected
        stream.write(
            json.dumps({"jsonrpc": "2.0", "method": "non_existent_method", "id": 7}).encode()
            + b"\n"
        )
        unk_line = stream.readline()
        unk_resp = json.loads(unk_line.decode())
        assert unk_resp["error"]["code"] == METHOD_NOT_FOUND

        # 9. Oversized payload over authentic IPC rejected / connection closed
        stream.write(b"x" * (MAX_MESSAGE_BYTES + 50) + b"\n")
        over_line = stream.readline()
        if over_line:
            over_resp = json.loads(over_line.decode())
            assert over_resp["error"]["code"] == PAYLOAD_TOO_LARGE

    finally:
        helper.close()
        server.stop()
        window._confirm_discard_changes = lambda: True  # Prevent modal QMessageBox
        window.close()
        assert server.info_file_path is not None and not server.info_file_path.exists()


def test_server_stop_during_active_connection(qtbot: QtBot) -> None:
    """Verify that stopping the server while a client is connected finishes promptly."""
    window = MainWindow(offer_recovery=False)
    qtbot.addWidget(window)
    server = DebugBridgeServer(window)
    server.start()

    helper = _ClientStreamHelper(server.endpoint_address)
    stream = helper.connect()

    start_stop = time.time()
    try:
        # Perform handshake to establish connection
        valid_hs = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "handshake",
                    "params": {"token": server.auth_token, "version": PROTOCOL_VERSION},
                    "id": 1,
                }
            ).encode()
            + b"\n"
        )
        stream.write(valid_hs)
        stream.readline()
    finally:
        server.stop()
        helper.close()
        window.close()
        duration = time.time() - start_stop
        assert duration < 5.0  # Server stop must unblock and terminate promptly
        assert server.info_file_path is not None and not server.info_file_path.exists()


def test_security_stale_session_cleanup(tmp_path: Path) -> None:
    """Verify that abandoned session files from dead PIDs are cleanly removed."""
    window_mock = MagicMock()
    server = DebugBridgeServer(window_mock)
    session_dir = tmp_path / "PyGeoLab" / "debug"
    session_dir.mkdir(parents=True)

    # Fake dead session file (PID 99999999)
    stale_file = session_dir / "session_99999999.json"
    stale_file.write_text('{"endpoint": "old", "token": "old"}', encoding="utf-8")

    server._cleanup_stale_sessions(session_dir)
    assert not stale_file.exists()


def test_security_symlink_rejection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that symlinked or reparse point session directory is rejected."""
    window_mock = MagicMock()
    server = DebugBridgeServer(window_mock)

    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    sym_dir = tmp_path / "sym_dir"
    try:
        sym_dir.symlink_to(real_dir, target_is_directory=True)
    except OSError:
        return  # Skip if symlink creation is not permitted on host

    if sys.platform == "win32":
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        debug_dir = tmp_path / "PyGeoLab" / "debug"
    else:
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        debug_dir = tmp_path / "pygeolab" / "debug"

    debug_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        debug_dir.symlink_to(real_dir, target_is_directory=True)
    except OSError:
        return

    with pytest.raises(PermissionError, match="untrusted symlink"):
        server._get_session_dir()


def test_windows_security_failure_handling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that failure of any Win32 security call raises PermissionError and cleans up."""
    if sys.platform != "win32":
        return

    import ctypes

    windll_obj = getattr(ctypes, "windll", None)
    if windll_obj is None:
        return

    window_mock = MagicMock()
    server = DebugBridgeServer(window_mock)
    session_dir = tmp_path / "debug"
    session_dir.mkdir()

    # 1. SDDL conversion failure in _get_session_dir
    monkeypatch.setattr(
        windll_obj.advapi32,
        "ConvertStringSecurityDescriptorToSecurityDescriptorW",
        lambda *args: 0,
    )
    with pytest.raises(PermissionError, match="Failed to convert security descriptor"):
        server._get_session_dir()

    # 2. SetFileSecurityW failure in _get_session_dir
    monkeypatch.undo()
    monkeypatch.setattr(windll_obj.advapi32, "SetFileSecurityW", lambda *args: 0)
    with pytest.raises(PermissionError, match="SetFileSecurityW failed"):
        server._get_session_dir()

    # 3. CreateFileW failure in _write_connection_file
    monkeypatch.undo()
    monkeypatch.setattr(windll_obj.kernel32, "CreateFileW", lambda *args: -1)
    with pytest.raises(PermissionError, match="Failed to create protected temp session file"):
        server._write_connection_file(session_dir)

    # 4. WriteFile failure in _write_connection_file
    monkeypatch.undo()
    monkeypatch.setattr(windll_obj.kernel32, "WriteFile", lambda *args: 0)
    with pytest.raises(PermissionError, match="Failed to write session secret"):
        server._write_connection_file(session_dir)

    # Ensure no leaked temp files in session_dir
    assert list(session_dir.glob("*.tmp")) == []

    # 5. Atomic replacement failure in _write_connection_file cleans up temp file
    monkeypatch.undo()

    def mock_replace(self: Path, target: Path) -> None:
        raise OSError("Simulated disk replacement error")

    monkeypatch.setattr(Path, "replace", mock_replace)
    with pytest.raises(OSError, match="Simulated disk replacement error"):
        server._write_connection_file(session_dir)

    assert list(session_dir.glob("*.tmp")) == []
    assert not (session_dir / f"session_{os.getpid()}.json").exists()


def test_verify_windows_dacl_comprehensive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that _verify_windows_dacl rejects permissive or invalid DACLs."""
    if sys.platform != "win32":
        return

    import ctypes

    windll_obj = getattr(ctypes, "windll", None)
    if windll_obj is None:
        return

    from pygeolab.debug.bridge import _verify_windows_dacl

    dummy_file = tmp_path / "dacl_test.txt"
    dummy_file.write_text("hello")

    # 1. Valid owner-only DACL passes
    p_sd_ok = ctypes.c_void_p()
    windll_obj.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        "D:P(A;;GA;;;OW)", 1, ctypes.byref(p_sd_ok), None
    )
    windll_obj.advapi32.SetFileSecurityW(str(dummy_file), 4, p_sd_ok)
    windll_obj.kernel32.LocalFree(p_sd_ok)
    _verify_windows_dacl(dummy_file)

    # 2. Reject permissive DACL granting Everyone (S-1-1-0) access
    p_sd_everyone = ctypes.c_void_p()
    windll_obj.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        "D:P(A;;GA;;;WD)", 1, ctypes.byref(p_sd_everyone), None
    )
    windll_obj.advapi32.SetFileSecurityW(str(dummy_file), 4, p_sd_everyone)
    windll_obj.kernel32.LocalFree(p_sd_everyone)
    with pytest.raises(PermissionError, match="forbidden permissive SID: S-1-1-0"):
        _verify_windows_dacl(dummy_file)

    # 3. Reject permissive DACL granting Authenticated Users (S-1-5-11) access
    p_sd_au = ctypes.c_void_p()
    windll_obj.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        "D:P(A;;GA;;;AU)", 1, ctypes.byref(p_sd_au), None
    )
    windll_obj.advapi32.SetFileSecurityW(str(dummy_file), 4, p_sd_au)
    windll_obj.kernel32.LocalFree(p_sd_au)
    with pytest.raises(PermissionError, match="forbidden permissive SID: S-1-5-11"):
        _verify_windows_dacl(dummy_file)

    # 4. Reject empty DACL (0 ACEs)
    p_sd_empty = ctypes.c_void_p()
    windll_obj.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        "D:P", 1, ctypes.byref(p_sd_empty), None
    )
    windll_obj.advapi32.SetFileSecurityW(str(dummy_file), 4, p_sd_empty)
    windll_obj.kernel32.LocalFree(p_sd_empty)
    with pytest.raises(PermissionError, match="0 ACEs"):
        _verify_windows_dacl(dummy_file)

    # Restore valid DACL for mocked failure tests
    p_sd_valid = ctypes.c_void_p()
    windll_obj.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        "D:P(A;;GA;;;OW)", 1, ctypes.byref(p_sd_valid), None
    )
    windll_obj.advapi32.SetFileSecurityW(str(dummy_file), 4, p_sd_valid)
    windll_obj.kernel32.LocalFree(p_sd_valid)

    # 5. Fail OpenProcessToken
    monkeypatch.setattr(windll_obj.advapi32, "OpenProcessToken", lambda *args: 0)
    with pytest.raises(PermissionError, match="OpenProcessToken failed"):
        _verify_windows_dacl(dummy_file)

    # 6. Fail GetTokenInformation
    monkeypatch.undo()
    monkeypatch.setattr(windll_obj.advapi32, "GetTokenInformation", lambda *args: 0)
    with pytest.raises(PermissionError, match="GetTokenInformation"):
        _verify_windows_dacl(dummy_file)

    # 7. Fail GetFileSecurityW
    monkeypatch.undo()
    monkeypatch.setattr(windll_obj.advapi32, "GetFileSecurityW", lambda *args: 0)
    with pytest.raises(PermissionError, match="GetFileSecurityW"):
        _verify_windows_dacl(dummy_file)

    # 8. Fail GetSecurityDescriptorOwner
    monkeypatch.undo()
    monkeypatch.setattr(windll_obj.advapi32, "GetSecurityDescriptorOwner", lambda *args: 0)
    with pytest.raises(PermissionError, match="Owner SID"):
        _verify_windows_dacl(dummy_file)

    # 9. Owner mismatch (EqualSid returns False)
    monkeypatch.undo()
    monkeypatch.setattr(windll_obj.advapi32, "EqualSid", lambda sid1, sid2: 0)
    with pytest.raises(PermissionError, match="owner SID .* does not match"):
        _verify_windows_dacl(dummy_file)

    # 10. Fail GetSecurityDescriptorDacl
    monkeypatch.undo()
    monkeypatch.setattr(windll_obj.advapi32, "GetSecurityDescriptorDacl", lambda *args: 0)
    with pytest.raises(PermissionError, match="NULL or missing DACL"):
        _verify_windows_dacl(dummy_file)

    # 11. Fail GetAclInformation
    monkeypatch.undo()
    monkeypatch.setattr(windll_obj.advapi32, "GetAclInformation", lambda *args: 0)
    with pytest.raises(PermissionError, match="GetAclInformation failed"):
        _verify_windows_dacl(dummy_file)

    # 12. Fail GetAce
    monkeypatch.undo()
    monkeypatch.setattr(windll_obj.advapi32, "GetAce", lambda *args: 0)
    with pytest.raises(PermissionError, match="GetAce"):
        _verify_windows_dacl(dummy_file)

    # 13. Unauthorized principal in ACE (Local Service S-1-5-19)
    monkeypatch.undo()
    p_sd_ls = ctypes.c_void_p()
    windll_obj.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        "D:P(A;;GA;;;LS)", 1, ctypes.byref(p_sd_ls), None
    )
    windll_obj.advapi32.SetFileSecurityW(str(dummy_file), 4, p_sd_ls)
    windll_obj.kernel32.LocalFree(p_sd_ls)
    with pytest.raises(PermissionError, match="unauthorized principal: S-1-5-19"):
        _verify_windows_dacl(dummy_file)


def test_server_shutdown_status_and_rejection() -> None:
    """Verify structured shutdown status and refusal of requests when stopped."""
    window_mock = MagicMock()
    server = DebugBridgeServer(window_mock)
    server.start()
    assert server.shutdown_status["stopped"] is False

    # Simulate request handling when server is shutting down
    server.running = False
    fake_stream = io.BytesIO(b'{"jsonrpc": "2.0", "method": "ping", "id": 1}\n')
    server._handle_client_stream(fake_stream)

    raw = fake_stream.getvalue().strip().decode("utf-8")
    assert raw
    err_resp = json.loads(raw)
    assert err_resp["error"]["code"] == SERVER_STOPPING

    server.stop()
    assert server.shutdown_status["stopped"] is True
    assert server.shutdown_status["clean"] is True
    assert server.shutdown_status["thread_alive"] is False


def test_server_incomplete_frame_handling() -> None:
    """Verify server cleanly terminates stream without crash when client sends incomplete frame."""
    window_mock = MagicMock()
    server = DebugBridgeServer(window_mock)
    server.running = True

    # Incomplete frame (no newline delimiter before EOF)
    fake_stream = io.BytesIO(b'{"jsonrpc": "2.0", "method": "ping"')
    server._handle_client_stream(fake_stream)
    server.running = False


def test_server_stop_timeout_structured_status() -> None:
    """Verify that when the server thread fails to terminate within timeout, status reflects it."""
    window_mock = MagicMock()
    server = DebugBridgeServer(window_mock)

    fake_thread = MagicMock()
    fake_thread.is_alive.return_value = True
    server._server_thread = fake_thread

    server.stop(timeout=0.01)
    assert server.shutdown_status["stopped"] is True
    assert server.shutdown_status["clean"] is False
    assert server.shutdown_status["thread_alive"] is True
    assert server._server_thread is fake_thread


def test_dispatch_collect_snapshot_error_handling() -> None:
    """Verify that _dispatch_collect_snapshot handles timeout and exceptions."""
    window_mock = MagicMock()
    server = DebugBridgeServer(window_mock)

    # 1. Event wait times out
    server.dispatcher.request_snapshot = MagicMock()
    with pytest.raises(TimeoutError, match="Timed out waiting"):
        server._dispatch_collect_snapshot()

    # 2. Qt thread sets an error
    def simulate_error(container: dict[str, Any]) -> None:
        container["error"] = ValueError("Simulated Qt thread error")
        container["event"].set()

    server.dispatcher.request_snapshot.emit = simulate_error
    with pytest.raises(ValueError, match="Simulated Qt thread error"):
        server._dispatch_collect_snapshot()


class _DuplexBytesIO:
    def __init__(self, incoming: bytes) -> None:
        self.incoming = io.BytesIO(incoming)
        self.outgoing = io.BytesIO()

    def read(self, n: int = -1) -> bytes:
        return self.incoming.read(n)

    def readline(self, size: int = -1) -> bytes:
        return self.incoming.readline(size)

    def write(self, data: bytes) -> int:
        return self.outgoing.write(data)


def test_server_handler_internal_error() -> None:
    """Verify that unhandled internal exceptions in server handler return safe error response."""
    window_mock = MagicMock()
    server = DebugBridgeServer(window_mock)
    server.running = True

    # Mock _dispatch_collect_snapshot to raise unexpected RuntimeError
    server._dispatch_collect_snapshot = MagicMock(side_effect=RuntimeError("Secret internal error"))

    # Handshake first
    hs_bytes = (
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "handshake",
                "params": {"token": server.auth_token, "version": "1.0.0"},
                "id": 1,
            }
        ).encode("utf-8")
        + b"\n"
    )
    snap_bytes = (
        json.dumps({"jsonrpc": "2.0", "method": "runtime_snapshot", "id": 2}).encode("utf-8")
        + b"\n"
    )

    stream = _DuplexBytesIO(hs_bytes + snap_bytes)
    server._handle_client_stream(stream)  # type: ignore[arg-type]
    server.running = False

    output = stream.outgoing.getvalue().decode("utf-8")
    assert "Secret internal error" not in output
    assert "Internal server error" in output
