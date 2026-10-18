"""Local IPC debug bridge server for PyGeoLab.

Runs a lightweight JSON-RPC server over Named Pipe (Windows) or Unix Domain Socket (Linux).
Dispatches requests cleanly to the Qt main thread to extract authentic runtime snapshots.
"""

from __future__ import annotations

import contextlib
import ctypes
import json
import logging
import msvcrt
import os
import secrets
import socket
import sys
import threading
import time
import typing
from pathlib import Path
from typing import Any, BinaryIO

from PySide6.QtCore import QObject, Signal, Slot

from pygeolab import __version__
from pygeolab.debug.inspector import RuntimeInspector
from pygeolab.debug.protocol import (
    AUTH_FAILED,
    METHOD_NOT_FOUND,
    PROTOCOL_MISMATCH,
    PROTOCOL_VERSION,
    ProtocolError,
    RequestEnvelope,
    build_error_response,
    build_response,
)
from pygeolab.ui.main_window import MainWindow

LOGGER = logging.getLogger(__name__)


class _QtDispatcher(QObject):
    """Bridge QObject to dispatch synchronous inspection requests to Qt main thread."""

    request_snapshot = Signal(object)

    def __init__(self, inspector: RuntimeInspector) -> None:
        super().__init__()
        self.inspector = inspector
        self.request_snapshot.connect(self._handle_snapshot)

    @Slot(object)
    def _handle_snapshot(self, container: dict[str, Any]) -> None:
        try:
            container["result"] = self.inspector.collect_snapshot()
        except Exception as exc:
            container["error"] = exc
        finally:
            evt: threading.Event = container["event"]
            evt.set()


class DebugBridgeServer:
    """IPC Server for PyGeoLab debug inspection."""

    def __init__(self, window: MainWindow) -> None:
        self.window = window
        self.start_time = time.time()
        self.inspector = RuntimeInspector(window, self.start_time)
        self.dispatcher = _QtDispatcher(self.inspector)

        self.auth_token = secrets.token_hex(32)
        self.running = False
        self._server_thread: threading.Thread | None = None
        self._pipe_handle: int | None = None
        self._unix_socket: socket.socket | None = None
        self.endpoint_address: str = ""
        self.info_file_path: Path | None = None

    def start(self) -> None:
        """Start the background IPC server and write secure connection info."""
        self.running = True
        if sys.platform == "win32":
            pipe_id = secrets.token_hex(8)
            self.endpoint_address = rf"\\.\pipe\pygeolab_debug_{os.getpid()}_{pipe_id}"
        else:  # pragma: no cover
            runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"  # noqa: S108
            self.endpoint_address = str(
                Path(runtime_dir) / f"pygeolab_debug_{os.getpid()}_{secrets.token_hex(8)}.sock"
            )

        self._write_connection_file()
        self._server_thread = threading.Thread(
            target=self._run_server, name="PyGeoLabDebugBridge", daemon=True
        )
        self._server_thread.start()
        LOGGER.info("PyGeoLab debug bridge server started on %s", self.endpoint_address)

    def _write_connection_file(self) -> None:
        """Write session auth and endpoint details to an owner-only file."""
        config_dir = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "PyGeoLab" / "debug"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.info_file_path = config_dir / f"session_{os.getpid()}.json"

        info = {
            "version": PROTOCOL_VERSION,
            "pygeolab_version": __version__,
            "pid": os.getpid(),
            "endpoint": self.endpoint_address,
            "token": self.auth_token,
        }

        # Write atomically with strict permissions
        temp_file = self.info_file_path.with_suffix(".tmp")
        if sys.platform != "win32":  # pragma: no cover
            fd = os.open(temp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(info, f)
        else:
            temp_file.write_text(json.dumps(info), encoding="utf-8")

        temp_file.replace(self.info_file_path)

    def stop(self) -> None:
        """Stop server, close open handles, and remove connection info file."""
        self.running = False
        if self.info_file_path and self.info_file_path.exists():
            with contextlib.suppress(Exception):
                self.info_file_path.unlink()

        if sys.platform == "win32":
            if self.endpoint_address:
                # Open quick dummy connection to unblock pending ConnectNamedPipe
                with contextlib.suppress(Exception):
                    h_dummy = ctypes.windll.kernel32.CreateFileW(
                        self.endpoint_address,
                        0xC0000000,
                        0,
                        None,
                        3,
                        0,
                        None,
                    )
                    if h_dummy and h_dummy != -1:
                        ctypes.windll.kernel32.CloseHandle(h_dummy)
            if self._pipe_handle is not None:
                with contextlib.suppress(Exception):
                    ctypes.windll.kernel32.CloseHandle(self._pipe_handle)
                self._pipe_handle = None
        else:  # pragma: no cover
            if self._unix_socket is not None:
                with contextlib.suppress(Exception):
                    self._unix_socket.close()
                self._unix_socket = None
            if self.endpoint_address and Path(self.endpoint_address).exists():
                with contextlib.suppress(Exception):
                    Path(self.endpoint_address).unlink()

        LOGGER.info("PyGeoLab debug bridge server stopped")

    def _run_server(self) -> None:
        """Main server loop accepting connections."""
        if sys.platform == "win32":
            self._run_windows_named_pipe()
        else:  # pragma: no cover
            self._run_unix_socket()

    def _run_windows_named_pipe(self) -> None:
        kernel32 = ctypes.windll.kernel32
        advapi32 = ctypes.windll.advapi32

        # Create security descriptor restricted to the current user (Owner Only)
        class SECURITY_ATTRIBUTES(ctypes.Structure):
            _fields_ = [
                ("nLength", ctypes.c_ulong),
                ("lpSecurityDescriptor", ctypes.c_void_p),
                ("bInheritHandle", ctypes.c_bool),
            ]

        sddl = "D:(A;;GA;;;OW)"  # Discretionary ACL: Allow Generic All to Owner
        p_sd = ctypes.c_void_p()
        advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, 1, ctypes.byref(p_sd), None
        )

        sa = SECURITY_ATTRIBUTES()
        sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
        sa.lpSecurityDescriptor = p_sd
        sa.bInheritHandle = False

        PIPE_ACCESS_DUPLEX = 3
        PIPE_TYPE_BYTE = 0
        PIPE_WAIT = 0

        while self.running:
            h_pipe = kernel32.CreateNamedPipeW(
                self.endpoint_address,
                PIPE_ACCESS_DUPLEX,
                PIPE_TYPE_BYTE | PIPE_WAIT,
                1,  # Max 1 client connection at a time
                65536,
                65536,
                0,
                ctypes.byref(sa),
            )
            if h_pipe == -1 or h_pipe == 0:
                break

            self._pipe_handle = h_pipe
            # Wait for client connection
            connected = kernel32.ConnectNamedPipe(h_pipe, None)
            last_err = kernel32.GetLastError()
            ERROR_PIPE_CONNECTED = 535
            if not connected and last_err != ERROR_PIPE_CONNECTED:
                kernel32.CloseHandle(h_pipe)
                continue

            try:
                fd = msvcrt.open_osfhandle(h_pipe, 0)
                with open(fd, "r+b", buffering=0) as stream:
                    self._handle_client_stream(stream)
            except Exception as exc:
                LOGGER.debug("Named pipe client disconnected: %s", exc)
            finally:
                with contextlib.suppress(Exception):
                    kernel32.DisconnectNamedPipe(h_pipe)
                with contextlib.suppress(Exception):
                    kernel32.CloseHandle(h_pipe)
                self._pipe_handle = None

        if p_sd:
            kernel32.LocalFree(p_sd)

    def _run_unix_socket(self) -> None:  # pragma: no cover
        af_unix = getattr(socket, "AF_UNIX", None)
        if af_unix is None:
            return
        sock = socket.socket(af_unix, socket.SOCK_STREAM)
        self._unix_socket = sock
        try:
            if Path(self.endpoint_address).exists():
                Path(self.endpoint_address).unlink()
            sock.bind(self.endpoint_address)
            os.chmod(self.endpoint_address, 0o600)
            sock.listen(1)
            sock.settimeout(1.0)
            while self.running:
                try:
                    conn, _ = sock.accept()
                except TimeoutError:
                    continue
                with conn:
                    conn.settimeout(3.0)
                    with conn.makefile("rwb", buffering=0) as stream:
                        self._handle_client_stream(typing.cast(BinaryIO, stream))
        except Exception as exc:
            if self.running:
                LOGGER.error("Unix socket server error: %s", exc)
        finally:
            with contextlib.suppress(Exception):
                sock.close()
            if Path(self.endpoint_address).exists():
                with contextlib.suppress(Exception):
                    Path(self.endpoint_address).unlink()

    def _handle_client_stream(self, stream: BinaryIO) -> None:
        """Handle JSON-RPC request-response loop over an established client stream."""
        authenticated = False
        while self.running:
            line = stream.readline()
            if not line:
                break
            req_id: str | int | None = None
            try:
                req = RequestEnvelope.from_bytes(line.strip())
                req_id = req.id
                if req.method == "handshake":
                    token = req.params.get("token")
                    client_ver = req.params.get("version")
                    if not secrets.compare_digest(str(token), self.auth_token):
                        raise ProtocolError(AUTH_FAILED, "Invalid session auth token")
                    if client_ver != PROTOCOL_VERSION:
                        msg = f"Version mismatch: expected {PROTOCOL_VERSION}, got {client_ver}"
                        raise ProtocolError(PROTOCOL_MISMATCH, msg)
                    authenticated = True
                    resp = build_response(
                        {
                            "status": "authenticated",
                            "version": PROTOCOL_VERSION,
                            "pygeolab_version": __version__,
                            "pid": os.getpid(),
                        },
                        req_id,
                    )
                    stream.write(resp)
                    continue

                if not authenticated:
                    raise ProtocolError(AUTH_FAILED, "Handshake required before executing methods")

                if req.method == "runtime_snapshot":
                    snapshot = self._dispatch_collect_snapshot()
                    resp = build_response(snapshot, req_id)
                    stream.write(resp)
                elif req.method == "ping":
                    resp = build_response({"pong": True, "time": time.time()}, req_id)
                    stream.write(resp)
                else:
                    raise ProtocolError(METHOD_NOT_FOUND, f"Method '{req.method}' not found")
            except ProtocolError as perr:
                stream.write(build_error_response(perr, req_id))
            except Exception as gerr:
                LOGGER.exception("Internal error in debug bridge handler: %s", gerr)
                stream.write(build_error_response(gerr, req_id))

    def _dispatch_collect_snapshot(self) -> dict[str, Any]:
        """Dispatch snapshot request to Qt main thread and await result safely."""
        container: dict[str, Any] = {"event": threading.Event()}
        self.dispatcher.request_snapshot.emit(container)
        completed = container["event"].wait(timeout=3.0)
        if not completed:
            raise TimeoutError("Timed out waiting for Qt main thread to generate runtime snapshot")
        if "error" in container:
            raise container["error"]
        result: dict[str, Any] = container["result"]
        return result
