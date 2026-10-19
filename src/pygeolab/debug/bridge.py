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
    SERVER_STOPPING,
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
OWNER_SECURITY_INFORMATION = 0x00000001
TOKEN_QUERY = 0x0008
TokenUser = 1
AclSizeInformation = 2


DWORD = wintypes.DWORD if wintypes is not None else ctypes.c_uint32
BYTE = wintypes.BYTE if wintypes is not None else ctypes.c_uint8
WORD = wintypes.WORD if wintypes is not None else ctypes.c_uint16


class SECURITY_ATTRIBUTES(ctypes.Structure):
    """Win32 SECURITY_ATTRIBUTES structure."""

    _fields_ = [
        ("nLength", ctypes.c_ulong),
        ("lpSecurityDescriptor", ctypes.c_void_p),
        ("bInheritHandle", ctypes.c_int),
    ]


class ACL_SIZE_INFORMATION(ctypes.Structure):
    """Win32 ACL_SIZE_INFORMATION structure."""

    _fields_ = [
        ("AceCount", DWORD),
        ("AclBytesInUse", DWORD),
        ("AclBytesFree", DWORD),
    ]


class ACE_HEADER(ctypes.Structure):
    """Win32 ACE_HEADER structure."""

    _fields_ = [
        ("AceType", BYTE),
        ("AceFlags", BYTE),
        ("AceSize", WORD),
    ]


class ACCESS_ALLOWED_ACE(ctypes.Structure):
    """Win32 ACCESS_ALLOWED_ACE structure."""

    _fields_ = [
        ("Header", ACE_HEADER),
        ("Mask", DWORD),
        ("SidStart", DWORD),
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

        advapi32.GetFileSecurityW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        advapi32.GetFileSecurityW.restype = wintypes.BOOL

        advapi32.GetSecurityDescriptorDacl.argtypes = [
            wintypes.LPVOID,
            ctypes.POINTER(wintypes.BOOL),
            ctypes.POINTER(wintypes.LPVOID),
            ctypes.POINTER(wintypes.BOOL),
        ]
        advapi32.GetSecurityDescriptorDacl.restype = wintypes.BOOL

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

        kernel32.WriteFile.argtypes = [
            wintypes.HANDLE,
            wintypes.LPCVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPVOID,
        ]
        kernel32.WriteFile.restype = wintypes.BOOL

        kernel32.GetLastError.argtypes = []
        kernel32.GetLastError.restype = wintypes.DWORD

        advapi32.OpenProcessToken.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.HANDLE),
        ]
        advapi32.OpenProcessToken.restype = wintypes.BOOL

        advapi32.GetTokenInformation.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        advapi32.GetTokenInformation.restype = wintypes.BOOL

        advapi32.GetSecurityDescriptorOwner.argtypes = [
            wintypes.LPVOID,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(wintypes.BOOL),
        ]
        advapi32.GetSecurityDescriptorOwner.restype = wintypes.BOOL

        advapi32.EqualSid.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        advapi32.EqualSid.restype = wintypes.BOOL

        advapi32.IsValidSid.argtypes = [ctypes.c_void_p]
        advapi32.IsValidSid.restype = wintypes.BOOL

        advapi32.CheckTokenMembership.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.BOOL),
        ]
        advapi32.CheckTokenMembership.restype = wintypes.BOOL

        advapi32.GetAclInformation.argtypes = [
            ctypes.c_void_p,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        advapi32.GetAclInformation.restype = wintypes.BOOL

        advapi32.GetAce.argtypes = [
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        advapi32.GetAce.restype = wintypes.BOOL

        advapi32.ConvertSidToStringSidW.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(wintypes.LPWSTR),
        ]
        advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL

        kernel32.GetCurrentProcess.argtypes = []
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE

        kernel32.CancelIoEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
        kernel32.CancelIoEx.restype = wintypes.BOOL

        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE


def _verify_windows_dacl(path: Path | str) -> None:  # pragma: no cover
    """Verify that a Windows path exists, is owned by user, and has owner-only DACL."""
    if sys.platform != "win32":
        return
    windll_obj = getattr(ctypes, "windll", None)
    if windll_obj is None:
        raise PermissionError("Win32 API unavailable to verify file security DACL")

    # 1. Obtain current process user SID
    h_token = wintypes.HANDLE()
    if not windll_obj.advapi32.OpenProcessToken(
        windll_obj.kernel32.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(h_token)
    ):
        err = windll_obj.kernel32.GetLastError()
        raise PermissionError(f"OpenProcessToken failed (error={err})")

    user_sid_str = ""
    try:
        needed_token = wintypes.DWORD(0)
        windll_obj.advapi32.GetTokenInformation(
            h_token, TokenUser, None, 0, ctypes.byref(needed_token)
        )
        if needed_token.value == 0:
            err = windll_obj.kernel32.GetLastError()
            raise PermissionError(f"GetTokenInformation size query failed (error={err})")
        token_buf = (ctypes.c_byte * needed_token.value)()
        if not windll_obj.advapi32.GetTokenInformation(
            h_token,
            TokenUser,
            ctypes.byref(token_buf),
            needed_token.value,
            ctypes.byref(needed_token),
        ):
            err = windll_obj.kernel32.GetLastError()
            raise PermissionError(f"GetTokenInformation failed (error={err})")
        p_user_sid = ctypes.cast(token_buf, ctypes.POINTER(ctypes.c_void_p)).contents
        p_sid_wstr = wintypes.LPWSTR()
        if windll_obj.advapi32.ConvertSidToStringSidW(p_user_sid, ctypes.byref(p_sid_wstr)):
            user_sid_str = p_sid_wstr.value or ""
            windll_obj.kernel32.LocalFree(p_sid_wstr)
    finally:
        windll_obj.kernel32.CloseHandle(h_token)

    # 2. Query Owner and DACL security descriptor
    needed = wintypes.DWORD(0)
    windll_obj.advapi32.GetFileSecurityW(
        str(path),
        OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION,
        None,
        0,
        ctypes.byref(needed),
    )
    if needed.value == 0:
        err = windll_obj.kernel32.GetLastError()
        raise PermissionError(f"GetFileSecurityW size query failed for {path} (error={err})")

    buf = (ctypes.c_byte * needed.value)()
    ok = windll_obj.advapi32.GetFileSecurityW(
        str(path),
        OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION,
        ctypes.byref(buf),
        needed.value,
        ctypes.byref(needed),
    )
    if not ok:
        err = windll_obj.kernel32.GetLastError()
        raise PermissionError(f"Failed to read security descriptor for {path} (error={err})")

    # 3. Verify Owner SID
    p_owner_sid = ctypes.c_void_p()
    owner_defaulted = wintypes.BOOL(0)
    owner_ok = windll_obj.advapi32.GetSecurityDescriptorOwner(
        ctypes.byref(buf), ctypes.byref(p_owner_sid), ctypes.byref(owner_defaulted)
    )
    if not owner_ok or not p_owner_sid.value or not windll_obj.advapi32.IsValidSid(p_owner_sid):
        raise PermissionError(f"Path {path} does not have a valid Owner SID in security descriptor")

    owner_matches = windll_obj.advapi32.EqualSid(p_owner_sid, p_user_sid)
    if not owner_matches and hasattr(windll_obj.advapi32, "CheckTokenMembership"):
        is_member = wintypes.BOOL(0)
        if (
            windll_obj.advapi32.CheckTokenMembership(None, p_owner_sid, ctypes.byref(is_member))
            and is_member.value
        ):
            owner_matches = True

    if not owner_matches:
        p_owner_wstr = wintypes.LPWSTR()
        owner_str = ""
        if windll_obj.advapi32.ConvertSidToStringSidW(p_owner_sid, ctypes.byref(p_owner_wstr)):
            owner_str = p_owner_wstr.value or ""
            windll_obj.kernel32.LocalFree(p_owner_wstr)
        raise PermissionError(
            f"Path {path} owner SID ({owner_str}) does not match current user SID ({user_sid_str})"
        )

    # 4. Verify DACL presence and non-NULL
    dacl_present = wintypes.BOOL(0)
    p_dacl = ctypes.c_void_p()
    dacl_defaulted = wintypes.BOOL(0)
    dacl_ok = windll_obj.advapi32.GetSecurityDescriptorDacl(
        ctypes.byref(buf),
        ctypes.byref(dacl_present),
        ctypes.byref(p_dacl),
        ctypes.byref(dacl_defaulted),
    )
    if not dacl_ok or not dacl_present.value or not p_dacl.value:
        raise PermissionError(f"Security descriptor for {path} has a NULL or missing DACL")

    # 5. Examine ACEs in DACL
    acl_info = ACL_SIZE_INFORMATION()
    if not windll_obj.advapi32.GetAclInformation(
        p_dacl, ctypes.byref(acl_info), ctypes.sizeof(acl_info), AclSizeInformation
    ):
        err = windll_obj.kernel32.GetLastError()
        raise PermissionError(f"GetAclInformation failed for {path} (error={err})")

    if acl_info.AceCount == 0:
        raise PermissionError(f"DACL for {path} has 0 ACEs")

    forbidden_sids = {
        "S-1-1-0",  # Everyone / World
        "S-1-5-11",  # Authenticated Users
        "S-1-5-32-545",  # Builtin Users
        "S-1-5-7",  # Anonymous
        "S-1-5-32-546",  # Guests
        "S-1-5-4",  # Interactive
        "S-1-5-2",  # Network
    }

    for i in range(acl_info.AceCount):
        p_ace = ctypes.c_void_p()
        if not windll_obj.advapi32.GetAce(p_dacl, i, ctypes.byref(p_ace)):
            err = windll_obj.kernel32.GetLastError()
            raise PermissionError(f"GetAce({i}) failed for {path} (error={err})")

        ace_sid_ptr = ctypes.c_void_p((p_ace.value or 0) + 8)
        if not windll_obj.advapi32.IsValidSid(ace_sid_ptr):
            raise PermissionError(f"ACE {i} on {path} contains an invalid SID")

        p_ace_sid_wstr = wintypes.LPWSTR()
        ace_sid_str = ""
        if windll_obj.advapi32.ConvertSidToStringSidW(ace_sid_ptr, ctypes.byref(p_ace_sid_wstr)):
            ace_sid_str = p_ace_sid_wstr.value or ""
            windll_obj.kernel32.LocalFree(p_ace_sid_wstr)

        if ace_sid_str in forbidden_sids:
            raise PermissionError(
                f"DACL for {path} contains forbidden permissive SID: {ace_sid_str}"
            )

        is_user = windll_obj.advapi32.EqualSid(ace_sid_ptr, p_user_sid)
        is_owner = windll_obj.advapi32.EqualSid(ace_sid_ptr, p_owner_sid)
        is_owner_rights = ace_sid_str == "S-1-3-4"
        ace_is_member = False
        if not (is_user or is_owner or is_owner_rights) and hasattr(
            windll_obj.advapi32, "CheckTokenMembership"
        ):
            b_member = wintypes.BOOL(0)
            if (
                windll_obj.advapi32.CheckTokenMembership(None, ace_sid_ptr, ctypes.byref(b_member))
                and b_member.value
            ):
                ace_is_member = True

        if not (is_user or is_owner or is_owner_rights or ace_is_member):
            raise PermissionError(
                f"DACL for {path} grants access to unauthorized principal: {ace_sid_str}"
            )


class _QtDispatcher(QObject):
    """Bridge QObject to dispatch synchronous inspection requests to Qt main thread."""

    request_snapshot = Signal(object)
    request_list_objects = Signal(object)
    request_inspect_object = Signal(object)

    def __init__(self, inspector: RuntimeInspector) -> None:
        super().__init__()
        self.inspector = inspector
        self.request_snapshot.connect(self._handle_snapshot)
        self.request_list_objects.connect(self._handle_list_objects)
        self.request_inspect_object.connect(self._handle_inspect_object)

    @Slot(object)
    def _handle_snapshot(self, container: dict[str, Any]) -> None:
        try:
            container["result"] = self.inspector.collect_snapshot()
        except Exception as exc:
            container["error"] = exc
        finally:
            evt: threading.Event = container["event"]
            evt.set()

    @Slot(object)
    def _handle_list_objects(self, container: dict[str, Any]) -> None:
        try:
            params = container.get("params", {})
            container["result"] = self.inspector.list_objects(
                limit=params.get("limit", 50),
                cursor=params.get("cursor"),
                kind=params.get("kind"),
            )
        except Exception as exc:
            container["error"] = exc
        finally:
            evt: threading.Event = container["event"]
            evt.set()

    @Slot(object)
    def _handle_inspect_object(self, container: dict[str, Any]) -> None:
        try:
            params = container.get("params", {})
            container["result"] = self.inspector.inspect_object(
                object_id=params.get("object_id", "")
            )
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
        self.shutdown_status: dict[str, Any] = {
            "stopped": False,
            "thread_alive": False,
            "clean": False,
            "error": None,
        }
        self._active_connections: dict[BinaryIO, Callable[[], None] | None] = {}
        self._connections_lock = threading.Lock()

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
            if windll_obj is None:
                raise PermissionError("Win32 API unavailable to secure session directory")
            p_sd = ctypes.c_void_p()
            sddl = "D:P(A;OICI;GA;;;OW)"  # Protected DACL: Allow Generic All to Owner only
            if (
                not windll_obj.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                    sddl, 1, ctypes.byref(p_sd), None
                )
                or not p_sd
            ):
                raise PermissionError("Failed to convert security descriptor for session directory")
            try:
                set_ok = windll_obj.advapi32.SetFileSecurityW(
                    str(session_dir),
                    DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION,
                    p_sd,
                )
                if not set_ok:
                    err = windll_obj.kernel32.GetLastError()
                    raise PermissionError(
                        f"SetFileSecurityW failed for session directory (error={err})"
                    )
            finally:
                windll_obj.kernel32.LocalFree(p_sd)
            _verify_windows_dacl(session_dir)
        else:
            if hasattr(os, "getuid"):
                st = session_dir.stat()
                if st.st_uid != os.getuid():
                    raise PermissionError(
                        f"Session directory {session_dir} is not owned by current user"
                    )
            os.chmod(session_dir, 0o700)
            st = session_dir.stat()
            if hasattr(os, "getuid") and st.st_uid != os.getuid():
                raise PermissionError(
                    f"Session directory {session_dir} is not owned by current user"
                )
            if st.st_mode & 0o077 != 0:
                raise PermissionError(f"Session directory {session_dir} has unsafe permissions")

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
            try:
                fd = os.open(temp_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                st = os.fstat(fd)
                if hasattr(os, "getuid") and st.st_uid != os.getuid():
                    os.close(fd)
                    raise PermissionError(
                        f"Temporary session file {temp_file} not owned by current user"
                    )
                if st.st_mode & 0o077 != 0:
                    os.close(fd)
                    raise PermissionError(
                        f"Temporary session file {temp_file} has unsafe permissions"
                    )
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(info, f)
                st_temp = temp_file.stat()
                if hasattr(os, "getuid") and st_temp.st_uid != os.getuid():
                    raise PermissionError(
                        f"Temporary session file {temp_file} not owned by current user"
                    )
                if st_temp.st_mode & 0o077 != 0:
                    raise PermissionError(
                        f"Temporary session file {temp_file} has unsafe permissions"
                    )
                temp_file.replace(self.info_file_path)
                st_final = self.info_file_path.stat()
                if hasattr(os, "getuid") and st_final.st_uid != os.getuid():
                    raise PermissionError(
                        f"Session file {self.info_file_path} not owned by current user"
                    )
                if st_final.st_mode & 0o077 != 0:
                    raise PermissionError(
                        f"Session file {self.info_file_path} has unsafe permissions"
                    )
            except Exception:
                if temp_file.exists():
                    with contextlib.suppress(Exception):
                        temp_file.unlink()
                if self.info_file_path.exists():
                    with contextlib.suppress(Exception):
                        self.info_file_path.unlink()
                raise
        else:  # pragma: no cover
            windll_obj = getattr(ctypes, "windll", None)
            if windll_obj is None:
                raise PermissionError("Win32 API unavailable to create secure session file")

            p_sd = ctypes.c_void_p()
            sddl = "D:P(A;;GA;;;OW)"  # Protected DACL: Owner Only Generic All
            if (
                not windll_obj.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                    sddl, 1, ctypes.byref(p_sd), None
                )
                or not p_sd
            ):
                raise PermissionError("Failed to convert security descriptor for session file")

            sa = SECURITY_ATTRIBUTES()
            sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
            sa.lpSecurityDescriptor = p_sd
            sa.bInheritHandle = 0

            h_file = -1
            try:
                try:
                    # Create file atomically with owner-only DACL BEFORE writing any secret
                    h_file = windll_obj.kernel32.CreateFileW(
                        str(temp_file),
                        0x40000000 | 0x80000000,  # GENERIC_READ | GENERIC_WRITE
                        0,  # Exclusive lock
                        ctypes.byref(sa),
                        1,  # CREATE_NEW
                        0x80,  # FILE_ATTRIBUTE_NORMAL
                        None,
                    )
                    if not h_file or h_file == -1:
                        err = windll_obj.kernel32.GetLastError()
                        raise PermissionError(
                            f"Failed to create protected temp session file (error={err})"
                        )

                    # Verify DACL and Owner policy on temporary file BEFORE writing secret
                    _verify_windows_dacl(temp_file)

                    raw_bytes = json.dumps(info).encode("utf-8")
                    written = wintypes.DWORD(0)
                    ok = windll_obj.kernel32.WriteFile(
                        h_file, raw_bytes, len(raw_bytes), ctypes.byref(written), None
                    )
                    if not ok or written.value != len(raw_bytes):
                        raise PermissionError("Failed to write session secret to temp file")
                finally:
                    if p_sd:
                        windll_obj.kernel32.LocalFree(p_sd)
                    if h_file and h_file != -1:
                        windll_obj.kernel32.CloseHandle(h_file)

                # Verify DACL of temp file before publication
                _verify_windows_dacl(temp_file)
                # Atomic rename/replace
                temp_file.replace(self.info_file_path)
                # Verify DACL of final published file
                _verify_windows_dacl(self.info_file_path)
            except Exception:
                if temp_file.exists():
                    with contextlib.suppress(Exception):
                        temp_file.unlink()
                if self.info_file_path.exists():
                    with contextlib.suppress(Exception):
                        self.info_file_path.unlink()
                raise

    def stop(self, timeout: float = 3.0) -> None:
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
                    res = windll_obj.kernel32.CancelIoEx(h, None)
                    if not res:
                        err = windll_obj.kernel32.GetLastError()
                        if err != 1168:  # ERROR_NOT_FOUND (no pending I/O)
                            LOGGER.debug("CancelIoEx returned code %d", err)

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

        # Close all active client connections immediately after canceling pending I/O
        with self._connections_lock:
            for active_conn, cancel_cb in list(self._active_connections.items()):
                if cancel_cb is not None:
                    with contextlib.suppress(Exception):
                        cancel_cb()
                with contextlib.suppress(Exception):
                    active_conn.close()
            self._active_connections.clear()

        if self._server_thread is not None and self._server_thread.is_alive():
            self._server_thread.join(timeout=timeout)
            if self._server_thread.is_alive():
                LOGGER.error("Server thread failed to terminate within %s seconds", timeout)
                self.shutdown_status = {
                    "stopped": True,
                    "thread_alive": True,
                    "clean": False,
                    "error": f"Server thread failed to terminate within {timeout}s",
                }
            else:
                self._server_thread = None
                self.shutdown_status = {
                    "stopped": True,
                    "thread_alive": False,
                    "clean": True,
                    "error": None,
                }
        else:
            self._server_thread = None
            self.shutdown_status = {
                "stopped": True,
                "thread_alive": False,
                "clean": True,
                "error": None,
            }

        LOGGER.info(
            "PyGeoLab debug bridge server stopped (clean=%s)", self.shutdown_status["clean"]
        )

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
            if sock_path.is_symlink():
                raise PermissionError(f"Socket path {sock_path} is an untrusted symlink")
            if sock_path.exists():
                if not sock_path.is_symlink() and stat.S_ISSOCK(sock_path.stat().st_mode):
                    sock_path.unlink()
                else:
                    raise PermissionError(f"Existing file at {sock_path} is not a valid socket")
            sock.bind(self.endpoint_address)
            os.chmod(self.endpoint_address, 0o600)
            st = sock_path.stat()
            if hasattr(os, "getuid") and st.st_uid != os.getuid():
                raise PermissionError(f"Socket {sock_path} not owned by current user")
            if st.st_mode & 0o077 != 0:
                raise PermissionError(f"Socket {sock_path} has unsafe permissions")
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

                        def unix_cancel_cb(s: socket.socket = conn) -> None:
                            with contextlib.suppress(Exception):
                                s.shutdown(socket.SHUT_RDWR)
                            with contextlib.suppress(Exception):
                                s.close()

                        self._handle_client_stream(
                            typing.cast(BinaryIO, stream), cancel_cb=unix_cancel_cb
                        )
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

        with self._connections_lock:
            self._active_connections[stream] = cancel_cb

        try:
            while request_count < max_requests_per_conn:
                if not self.running:
                    with contextlib.suppress(Exception):
                        stream.write(
                            build_error_response(
                                ProtocolError(SERVER_STOPPING, "Debug bridge is shutting down"),
                                None,
                            )
                        )
                    break

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
                        if hasattr(stream, "flush"):
                            stream.flush()
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

                    if not self.running:
                        with contextlib.suppress(Exception):
                            stream.write(
                                build_error_response(
                                    ProtocolError(SERVER_STOPPING, "Debug bridge is shutting down"),
                                    req_id,
                                )
                            )
                        break

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
                    elif req.method == "list_objects":
                        list_res = self._dispatch_list_objects(req.params)
                        resp = build_response(list_res, req_id)
                        stream.write(resp)
                    elif req.method == "inspect_object":
                        inspect_res = self._dispatch_inspect_object(req.params)
                        resp = build_response(inspect_res, req_id)
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
        finally:
            with self._connections_lock:
                self._active_connections.pop(stream, None)

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

    def _dispatch_list_objects(self, params: dict[str, Any]) -> dict[str, Any]:
        """Dispatch list_objects request to Qt main thread and await result safely."""
        container: dict[str, Any] = {"event": threading.Event(), "params": params}
        self.dispatcher.request_list_objects.emit(container)
        completed = container["event"].wait(timeout=3.0)
        if not completed:
            raise TimeoutError("Timed out waiting for Qt main thread to list objects")
        if "error" in container:
            raise container["error"]
        result: dict[str, Any] = container["result"]
        return result

    def _dispatch_inspect_object(self, params: dict[str, Any]) -> dict[str, Any]:
        """Dispatch inspect_object request to Qt main thread and await result safely."""
        container: dict[str, Any] = {"event": threading.Event(), "params": params}
        self.dispatcher.request_inspect_object.emit(container)
        completed = container["event"].wait(timeout=3.0)
        if not completed:
            raise TimeoutError("Timed out waiting for Qt main thread to inspect object")
        if "error" in container:
            raise container["error"]
        result: dict[str, Any] = container["result"]
        return result
