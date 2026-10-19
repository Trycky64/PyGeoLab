"""Structured JSON-RPC protocol definition for the PyGeoLab debug bridge."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

PROTOCOL_VERSION = "1.0.0"
MAX_MESSAGE_BYTES = 1024 * 1024  # 1 MB max request/response payload


class ProtocolError(Exception):
    """Base error for debug bridge protocol violations."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self) -> dict[str, Any]:
        """Convert error to JSON-RPC error mapping."""
        err: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            err["data"] = self.data
        return err


# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Application-specific error codes
AUTH_FAILED = -32000
PROTOCOL_MISMATCH = -32001
PAYLOAD_TOO_LARGE = -32002
SERVER_STOPPING = -32003
OBJECT_NOT_FOUND = -32004
DOCUMENT_REVISION_MISMATCH = -32005


@dataclass(frozen=True)
class RequestEnvelope:
    """Parsed JSON-RPC request."""

    method: str
    params: dict[str, Any]
    id: str | int | None

    @classmethod
    def from_bytes(cls, raw: bytes) -> RequestEnvelope:
        """Parse and validate raw request bytes."""
        if len(raw) > MAX_MESSAGE_BYTES:
            raise ProtocolError(
                PAYLOAD_TOO_LARGE, f"Message exceeds limit of {MAX_MESSAGE_BYTES} bytes"
            )
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise ProtocolError(PARSE_ERROR, f"Malformed JSON: {exc}") from exc

        if not isinstance(payload, Mapping):
            raise ProtocolError(INVALID_REQUEST, "Request payload must be a JSON object")

        if payload.get("jsonrpc") != "2.0":
            raise ProtocolError(
                INVALID_REQUEST, "Missing or invalid jsonrpc version (must be '2.0')"
            )

        method = payload.get("method")
        if not isinstance(method, str) or not method:
            raise ProtocolError(INVALID_REQUEST, "Method must be a non-empty string")

        params = payload.get("params", {})
        if not isinstance(params, Mapping):
            raise ProtocolError(INVALID_PARAMS, "Params must be a JSON object if provided")

        req_id = payload.get("id")
        if req_id is not None and not isinstance(req_id, (str, int)):
            raise ProtocolError(INVALID_REQUEST, "Request ID must be string, integer or null")

        return cls(method=method, params=dict(params), id=req_id)


def read_bounded_frame(stream: Any, max_bytes: int = MAX_MESSAGE_BYTES) -> bytes:
    """Read a single newline-terminated frame from stream bounded by max_bytes.

    Returns the stripped frame bytes (without trailing newline).

    Raises:
        EOFError: if stream is at EOF before any bytes are read.
        ProtocolError(PAYLOAD_TOO_LARGE): if frame exceeds max_bytes.
        ProtocolError(PARSE_ERROR): if stream reaches EOF before encountering newline.
    """
    chunk: bytes = stream.readline(max_bytes + 1)
    if not chunk:
        raise EOFError("Connection closed")

    if not chunk.endswith(b"\n"):
        if len(chunk) >= max_bytes:
            raise ProtocolError(
                PAYLOAD_TOO_LARGE,
                f"Message exceeds maximum size limit of {max_bytes} bytes",
            )
        raise ProtocolError(
            PARSE_ERROR,
            "Incomplete frame: stream closed before newline delimiter",
        )

    if len(chunk) > max_bytes:
        raise ProtocolError(
            PAYLOAD_TOO_LARGE,
            f"Message exceeds maximum size limit of {max_bytes} bytes",
        )

    return chunk[:-1]


def build_response(result: Any, req_id: str | int | None) -> bytes:
    """Build a JSON-RPC success response terminated by newline, enforcing payload limit."""
    payload = {
        "jsonrpc": "2.0",
        "result": result,
        "id": req_id,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8") + b"\n"
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ProtocolError(
            PAYLOAD_TOO_LARGE,
            f"Response payload exceeds maximum limit of {MAX_MESSAGE_BYTES} bytes",
        )
    return raw


def build_error_response(error: ProtocolError | Exception, req_id: str | int | None) -> bytes:
    """Build a sanitized JSON-RPC error response terminated by newline."""
    if isinstance(error, ProtocolError):
        err_dict = error.to_dict()
    else:
        # Never leak raw internal exception strings or tracebacks over IPC
        err_dict = {"code": INTERNAL_ERROR, "message": "Internal server error"}

    payload = {
        "jsonrpc": "2.0",
        "error": err_dict,
        "id": req_id,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8") + b"\n"
    if len(raw) > MAX_MESSAGE_BYTES:
        return (
            b'{"jsonrpc":"2.0","error":{"code":-32002,"message":"Payload too large"},"id":null}\n'
        )
    return raw
