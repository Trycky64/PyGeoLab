"""Local IPC debug bridge server for PyGeoLab.

Runs a lightweight JSON-RPC server over Named Pipe (Windows) or Unix Domain Socket (Linux).
Dispatches requests cleanly to the Qt main thread to extract authentic runtime snapshots.
"""

from __future__ import annotations

import contextlib
import ctypes
import json
import logging
import os
import secrets
import socket
import stat
import sys
import threading
import time
import typing
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO

if sys.platform == "win32":
    import msvcrt
    from ctypes import wintypes
else:
    msvcrt: Any = None
    wintypes: Any = None

from PySide6.QtCore import QObject, Signal, Slot

from pygeolab import __version__
from pygeolab.debug.inspector import RuntimeInspector
from pygeolab.debug.protocol import (
    AUTH_FAILED,
    MAX_MESSAGE_BYTES,
    METHOD_NOT_FOUND,
    PROTOCOL_MISMATCH,
    PROTOCOL_VERSION,
    ProtocolError,
    RequestEnvelope,
    build_error_response,
    build_response,
    read_bounded_frame,
)
from pygeolab.ui.main_window import MainWindow

LOGGER = logging.getLogger(__name__)

# Windows API Constants
PIPE_ACCESS_DUPLEX = 0x00000003
FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000
PIPE_TYPE_BYTE = 0x00000000
PIPE_WAIT = 0x00000000
PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
ERROR_PIPE_CONNECTED = 535
DACL_SECURITY_INFORMATION = 0x00000004
PROTECTED_DACL_SECURITY_INFORMATION = 0x80000000
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class SECURITY_ATTRIBUTES(ctypes.Structure):
    """Win32 SECURITY_ATTRIBUTES structure."""

    _fields_ = [
        ("nLength", ctypes.c_ulong),
        ("lpSecurityDescriptor", ctypes.c_void_p),
        ("bInheritHandle", ctypes.c_int),
    ]


if sys.platform == "win32":  # pragma: no cover
    windll = getattr(ctypes, "windll", None)
    if windll is not None:
        advapi32 = windll.advapi32
        kernel32 = windll.kernel32

        advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.LPVOID),
            ctypes.POINTER(wintypes.ULONG),
        ]
        advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL

        advapi32.SetFileSecurityW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.LPVOID,
        ]
        advapi32.SetFileSecurityW.restype = wintypes.BOOL

        kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
        kernel32.LocalFree.restype = wintypes.HLOCAL

        kernel32.CreateNamedPipeW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(SECURITY_ATTRIBUTES),
        ]
        kernel32.CreateNamedPipeW.restype = wintypes.HANDLE

        kernel32.ConnectNamedPipe.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
        kernel32.ConnectNamedPipe.restype = wintypes.BOOL

        kernel32.DisconnectNamedPipe.argtypes = [wintypes.HANDLE]
        kernel32.DisconnectNamedPipe.restype = wintypes.BOOL

        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        kernel32.CreateFileW.restype = wintypes.HANDLE

        kernel32.GetLastError.argtypes = []
        kernel32.GetLastError.restype = wintypes.DWORD

        kernel32.CancelIoEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
        kernel32.CancelIoEx.restype = wintypes.BOOL

        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE


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
    """Hardened IPC Server for PyGeoLab debug inspection."""

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

    def _get_session_dir(self) -> Path:
        """Resolve, validate, and secure the private session directory."""
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA")
            base_dir = Path(base) if base else Path.home() / "AppData" / "Local"
            session_dir = base_dir / "PyGeoLab" / "debug"
        else:
            xdg = os.environ.get("XDG_RUNTIME_DIR")
            if xdg and Path(xdg).exists():
                session_dir = Path(xdg) / "pygeolab" / "debug"
            else:
                session_dir = Path.home() / ".local" / "share" / "pygeolab" / "debug"

        # Verify against symlink or reparse point substitution
        if session_dir.exists():
            if session_dir.is_symlink():
                raise PermissionError(f"Session directory {session_dir} is an untrusted symlink")
            if sys.platform == "win32":
                st = session_dir.stat()
                if getattr(st, "st_file_attributes", 0) & 0x0400:  # FILE_ATTRIBUTE_REPARSE_POINT
                    raise PermissionError(
                        f"Session directory {session_dir} is an untrusted reparse point"
                    )
        else:
            session_dir.mkdir(parents=True, exist_ok=True)

        # Apply restricted DACL (Windows) or 0700 mode (Unix)
        if sys.platform == "win32":  # pragma: no cover
            windll_obj = getattr(ctypes, "windll", None)
            if windll_obj is not None:
                p_sd = ctypes.c_void_p()
                sddl = "D:P(A;OICI;GA;;;OW)"  # Protected DACL: Allow Generic All to Owner only
                if windll_obj.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                    sddl, 1, ctypes.byref(p_sd), None
                ):
                    try:
                        windll_obj.advapi32.SetFileSecurityW(
                            str(session_dir),
                            DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION,
                            p_sd,
                        )
                    finally:
                        windll_obj.kernel32.LocalFree(p_sd)
        else:
            with contextlib.suppress(OSError):
                os.chmod(session_dir, 0o700)

        return session_dir

    def _cleanup_stale_sessions(self, session_dir: Path) -> None:
        """Safely clean up dead or abandoned session files."""
        current_pid = os.getpid()
        for path in session_dir.glob("session_*.json"):
            if path.is_symlink():
                continue
            name = path.stem
            try:
                pid = int(name.split("_")[1])
            except (IndexError, ValueError):
                continue
            if pid == current_pid:
                continue

            is_alive = False
            if sys.platform == "win32":  # pragma: no cover
                windll_obj = getattr(ctypes, "windll", None)
                if windll_obj is not None:
                    h_proc = windll_obj.kernel32.OpenProcess(
                        PROCESS_QUERY_LIMITED_INFORMATION, False, pid
                    )
                    if h_proc and h_proc != -1:
                        windll_obj.kernel32.CloseHandle(h_proc)
                        is_alive = True
            else:
                try:
                    os.kill(pid, 0)
                    is_alive = True
                except (OSError, ProcessLookupError):
                    is_alive = False

            if not is_alive:
                with contextlib.suppress(Exception):
                    path.unlink()

    def start(self) -> None:
        """Start the background IPC server and write secure connection info."""
        self.running = True
        session_dir = self._get_session_dir()
        self._cleanup_stale_sessions(session_dir)

        if sys.platform == "win32":
            pipe_id = secrets.token_hex(8)
            self.endpoint_address = rf"\\.\pipe\pygeolab_debug_{os.getpid()}_{pipe_id}"
        else:  # pragma: no cover
            self.endpoint_address = str(
                session_dir / f"pygeolab_debug_{os.getpid()}_{secrets.token_hex(8)}.sock"
            )

        self._write_connection_file(session_dir)
        self._server_thread = threading.Thread(
            target=self._run_server, name="PyGeoLabDebugBridge", daemon=True
        )
        self._server_thread.start()
        LOGGER.info("PyGeoLab debug bridge server started on %s", self.endpoint_address)

    def _write_connection_file(self, session_dir: Path) -> None:
        """Write session auth and endpoint details to an owner-only file atomically."""
        self.info_file_path = session_dir / f"session_{os.getpid()}.json"

        info = {
            "version": PROTOCOL_VERSION,
            "pygeolab_version": __version__,
            "pid": os.getpid(),
            "endpoint": self.endpoint_address,
            "token": self.auth_token,
        }

        temp_file = session_dir / f"session_{os.getpid()}_{secrets.token_hex(4)}.tmp"
        if sys.platform != "win32":  # pragma: no cover
            fd = os.open(temp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(info, f)
        else:
            temp_file.write_text(json.dumps(info), encoding="utf-8")
            windll_obj = getattr(ctypes, "windll", None)
            if windll_obj is not None:
                p_sd = ctypes.c_void_p()
                sddl = "D:P(A;;GA;;;OW)"
                if windll_obj.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                    sddl, 1, ctypes.byref(p_sd), None
                ):
                    try:
                        windll_obj.advapi32.SetFileSecurityW(
                            str(temp_file),
                            DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION,
                            p_sd,
                        )
                    finally:
                        windll_obj.kernel32.LocalFree(p_sd)

        temp_file.replace(self.info_file_path)

    def stop(self) -> None:
        """Stop server, unblock pending operations, close handles, and remove connection info."""
        self.running = False
        if self.info_file_path and self.info_file_path.exists():
            with contextlib.suppress(Exception):
                self.info_file_path.unlink()

        if sys.platform == "win32":  # pragma: no cover
            windll_obj = getattr(ctypes, "windll", None)
            if windll_obj is not None:
                h = self._pipe_handle
                if h is not None and h != -1:
                    with contextlib.suppress(Exception):
                        windll_obj.kernel32.CancelIoEx(h, None)

                if self.endpoint_address:
                    with contextlib.suppress(Exception):
                        h_dummy = windll_obj.kernel32.CreateFileW(
                            self.endpoint_address,
                            0xC0000000,
                            0,
                            None,
                            3,
                            0,
                            None,
                        )
                        if h_dummy and h_dummy != -1:
                            windll_obj.kernel32.CloseHandle(h_dummy)
        else:  # pragma: no cover
            if self._unix_socket is not None:
                with contextlib.suppress(Exception):
                    self._unix_socket.close()
                self._unix_socket = None
            if self.endpoint_address and Path(self.endpoint_address).exists():
                with contextlib.suppress(Exception):
                    Path(self.endpoint_address).unlink()

        if self._server_thread is not None and self._server_thread.is_alive():
            self._server_thread.join(timeout=2.0)
            self._server_thread = None

        LOGGER.info("PyGeoLab debug bridge server stopped")

    def _run_server(self) -> None:
        """Main server loop accepting connections."""
        if sys.platform == "win32":
            self._run_windows_named_pipe()
        else:  # pragma: no cover
            self._run_unix_socket()

    def _run_windows_named_pipe(self) -> None:  # pragma: no cover
        windll_obj = getattr(ctypes, "windll", None)
        if windll_obj is None or msvcrt is None:
            return

        kernel32 = windll_obj.kernel32
        advapi32 = windll_obj.advapi32

        sddl = "D:(A;;GA;;;OW)"  # Discretionary ACL: Allow Generic All to Owner only
        p_sd = ctypes.c_void_p()
        if (
            not advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                sddl, 1, ctypes.byref(p_sd), None
            )
            or not p_sd
        ):
            LOGGER.error("Failed to convert security descriptor for named pipe")
            return

        sa = SECURITY_ATTRIBUTES()
        sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
        sa.lpSecurityDescriptor = p_sd
        sa.bInheritHandle = False

        dw_open_mode = PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE
        dw_pipe_mode = PIPE_TYPE_BYTE | PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS

        open_osfhandle = getattr(msvcrt, "open_osfhandle", None)
        if open_osfhandle is None:
            advapi32.LocalFree(p_sd)
            return

        try:
            while self.running:
                h_pipe = kernel32.CreateNamedPipeW(
                    self.endpoint_address,
                    dw_open_mode,
                    dw_pipe_mode,
                    1,  # Max 1 client connection at a time
                    MAX_MESSAGE_BYTES + 4096,
                    MAX_MESSAGE_BYTES + 4096,
                    0,
                    ctypes.byref(sa),
                )
                if h_pipe == -1 or h_pipe == 0:
                    break

                self._pipe_handle = h_pipe
                connected = kernel32.ConnectNamedPipe(h_pipe, None)
                last_err = kernel32.GetLastError()
                if not connected and last_err != ERROR_PIPE_CONNECTED:
                    kernel32.CloseHandle(h_pipe)
                    self._pipe_handle = None
                    continue

                stream_opened = False
                try:
                    fd = open_osfhandle(h_pipe, 0)
                    stream_opened = True
                    stream = open(fd, "r+b", buffering=0)

                    def cancel_cb(h: int = h_pipe) -> None:
                        kernel32.CancelIoEx(h, None)

                    try:
                        self._handle_client_stream(
                            stream,
                            cancel_cb=cancel_cb,
                        )
                    finally:
                        time.sleep(0.05)
                        with contextlib.suppress(Exception):
                            kernel32.DisconnectNamedPipe(h_pipe)
                        stream.close()
                except Exception as exc:
                    LOGGER.debug("Named pipe client disconnected: %s", exc)
                finally:
                    if not stream_opened:
                        with contextlib.suppress(Exception):
                            kernel32.CloseHandle(h_pipe)
                    self._pipe_handle = None
        finally:
            if p_sd:
                kernel32.LocalFree(p_sd)

    def _run_unix_socket(self) -> None:  # pragma: no cover
        af_unix = getattr(socket, "AF_UNIX", None)
        if af_unix is None:
            return
        sock = socket.socket(af_unix, socket.SOCK_STREAM)
        self._unix_socket = sock
        try:
            sock_path = Path(self.endpoint_address)
            if sock_path.exists():
                # Verify safety before removing
                if not sock_path.is_symlink() and stat.S_ISSOCK(sock_path.stat().st_mode):
                    sock_path.unlink()
            sock.bind(self.endpoint_address)
            with contextlib.suppress(OSError):
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

    def _handle_client_stream(
        self, stream: BinaryIO, cancel_cb: Callable[[], None] | None = None
    ) -> None:
        """Handle bounded JSON-RPC request-response loop over an established client stream."""
        authenticated = False
        request_count = 0
        max_requests_per_conn = 1000

        while self.running and request_count < max_requests_per_conn:
            watchdog: threading.Timer | None = None
            if cancel_cb is not None:
                watchdog = threading.Timer(3.0, cancel_cb)
                watchdog.daemon = True
                watchdog.start()

            try:
                raw_frame = read_bounded_frame(stream, MAX_MESSAGE_BYTES)
            except EOFError:
                break
            except ProtocolError as perr:
                with contextlib.suppress(Exception):
                    stream.write(build_error_response(perr, None))
                break  # Close connection on framing violation or payload excess
            except OSError as oerr:
                LOGGER.debug("Client stream aborted or timed out: %s", oerr)
                break
            finally:
                if watchdog is not None:
                    watchdog.cancel()

            request_count += 1
            req_id: str | int | None = None
            try:
                req = RequestEnvelope.from_bytes(raw_frame)
                req_id = req.id
                if req.method == "handshake":
                    token = req.params.get("token")
                    client_ver = req.params.get("version")
                    if not isinstance(token, str) or not secrets.compare_digest(
                        token, self.auth_token
                    ):
                        raise ProtocolError(AUTH_FAILED, "Invalid session auth token")
                    if client_ver != PROTOCOL_VERSION:
                        msg = (
                            f"Incompatible protocol version: {client_ver} "
                            f"(expected {PROTOCOL_VERSION})"
                        )
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
                    raise ProtocolError(
                        AUTH_FAILED, "Authentication required. Perform handshake first."
                    )

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
