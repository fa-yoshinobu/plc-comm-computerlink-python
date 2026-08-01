from __future__ import annotations

import math
import socket
import struct
import time
from _thread import LockType
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from ipaddress import ip_address
from queue import Empty, Full, Queue
from threading import Condition, Event, Lock, RLock, Thread, local
from typing import TypeVar, cast

from .address import encode_fr_word_addr32, fr_block_ex_no
from .errors import (
    ToyopucCancelledError,
    ToyopucClosedError,
    ToyopucError,
    ToyopucNotConnectedError,
    ToyopucOperationOutcomeUnknownError,
    ToyopucOutcomeUnknownReason,
    ToyopucPlcError,
    ToyopucProtocolError,
    ToyopucTimeoutError,
    ToyopucTransportError,
)
from .protocol import (
    FT_RESPONSE,
    ClockData,
    CpuStatusData,
    ResponseFrame,
    _build_relay_command_trimmed,
    _build_relay_nested_parsed,
    _parse_relay_inner_request,
    _RelayInnerRequest,
    build_bit_read,
    build_bit_write,
    build_byte_read,
    build_byte_write,
    build_clock_read,
    build_clock_write,
    build_command,
    build_cpu_status_read,
    build_cpu_status_read_a0,
    build_ext_byte_read,
    build_ext_byte_write,
    build_ext_multi_read,
    build_ext_multi_write,
    build_ext_word_read,
    build_ext_word_write,
    build_fr_register,
    build_multi_byte_read,
    build_multi_byte_write,
    build_multi_word_read,
    build_multi_word_write,
    build_pc10_block_read,
    build_pc10_block_write,
    build_pc10_multi_read,
    build_pc10_multi_write,
    build_scan_resume,
    build_scan_stop,
    build_scan_stop_release,
    build_word_read,
    build_word_write,
    parse_clock_data,
    parse_cpu_status_data,
    parse_cpu_status_data_a0,
    parse_cpu_status_data_a0_raw,
    parse_response,
    unpack_u16_le,
)
from .relay import (
    normalize_relay_hops,
    parse_relay_inner_response,
    unwrap_relay_response_chain,
)

_T = TypeVar("_T")


@dataclass(frozen=True)
class ToyopucTrafficStats:
    """Immutable lifetime traffic counters for one client."""

    request_count: int
    tx_bytes: int
    rx_bytes: int


class ToyopucTraceDirection(Enum):
    """Direction for a traced TOYOPUC computer-link frame."""

    SEND = "send"
    RECEIVE = "receive"


@dataclass(frozen=True)
class ToyopucTraceFrame:
    """One raw TOYOPUC frame observed by a trace hook."""

    direction: ToyopucTraceDirection
    data: bytes
    timestamp: datetime


ERROR_CODE_DESCRIPTIONS = {
    0x11: "CPU module hardware failure",
    0x20: "Relay command ENQ fixed data is not 0x05",
    0x21: "Invalid transfer number in relay command",
    0x23: "Invalid command code",
    0x24: "Invalid subcommand code",
    0x25: "Invalid command-format data byte",
    0x26: "Invalid function-call operand count",
    0x31: "Write or function call prohibited during sequence operation",
    0x32: "Command not executable during stop continuity",
    0x33: "Debug function called while not in debug mode",
    0x34: "Access prohibited by configuration",
    0x35: "Execution-priority limiting configuration prohibits execution",
    0x36: "Execution-priority limiting by another device prohibits execution",
    0x39: "Reset required after writing I/O parameters before scan start",
    0x3C: "Command not executable during fatal failure",
    0x3D: "Competing process prevents execution",
    0x3E: "Command not executable because reset exists",
    0x3F: "Command not executable because of stop duration",
    0x40: "Address or address+count is out of range",
    0x41: "Word/byte count is out of range",
    0x42: "Undesignated data was sent",
    0x43: "Invalid function-call operand",
    0x52: "Timer/counter set or current value access command mismatch",
    0x66: "No reply from relay link module",
    0x70: "Relay link module not executable",
    0x72: "No reply from relay link module",
    0x73: "Relay command collision on same link module; retry required",
}


UDP_RECEIVE_BUFFER_SIZE = 65_535
_FR_BLOCK_WORDS = 0x8000
_FR_MAX_INDEX = 0x1FFFFF
_FR_IO_CHUNK_WORDS = 0x01F8
_MAX_TIMER_SECONDS = 2_147_483.647
_EMPTY_STATE_RESPONSE_COMMANDS = {0x1D, 0x1F, 0x21, 0x23, 0x25, 0x95, 0x97, 0x99, 0xC3, 0xC5, 0xCA}


@dataclass
class _OperationAdmission:
    generation: int
    timeout: float
    cancel_event: Event


def _remaining_time(deadline: float, message: str) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ToyopucTimeoutError(message)
    return remaining


def _native_cause(error: BaseException) -> BaseException:
    cause = error
    while cause.__cause__ is not None:
        cause = cause.__cause__
    return cause


def _snapshot_operation_argument(value: object) -> object:
    """Detach mutable and one-shot public inputs before queue admission."""

    if isinstance(value, (str, bytes)):
        return value
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)
    if isinstance(value, Mapping):
        return {_snapshot_operation_argument(key): _snapshot_operation_argument(item) for key, item in value.items()}
    if isinstance(value, Iterable):
        return tuple(_snapshot_operation_argument(item) for item in value)
    return value


def _validate_fr_index(index: int) -> int:
    if isinstance(index, bool) or not isinstance(index, int) or index < 0 or index > _FR_MAX_INDEX:
        raise ValueError("FR index out of range (0x000000-0x1FFFFF)")
    return index


def _validate_fr_single_request(start_index: int, word_count: int) -> tuple[int, int]:
    index = _validate_fr_index(start_index)
    if isinstance(word_count, bool) or not isinstance(word_count, int) or word_count < 1:
        raise ValueError("word_count must be an integer >= 1")
    end = index + word_count - 1
    if end > _FR_MAX_INDEX:
        raise ValueError("FR range exceeds 0x1FFFFF")
    if index // _FR_BLOCK_WORDS != end // _FR_BLOCK_WORDS:
        raise ValueError("FR operation must stay within one 0x8000-word block")
    if word_count > _FR_IO_CHUNK_WORDS:
        raise ValueError(f"FR operation exceeds the single-request limit of {_FR_IO_CHUNK_WORDS} words")
    return index, word_count


def _validate_fr_block_start(index: int) -> int:
    block_start = _validate_fr_index(index)
    if block_start % _FR_BLOCK_WORDS != 0:
        raise ValueError("FR commit index must be the first word of a 0x8000-word block")
    return block_start


def _normalize_fr_word_values(values: Iterable[int]) -> list[int]:
    normalized: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFF:
            raise ValueError("FR word values must be integers in the range 0..65535")
        normalized.append(value)
    if not normalized:
        raise ValueError("values must contain at least one word")
    return normalized


def _normalize_unsigned_values(values: Iterable[int], *, bits: int, label: str) -> list[int]:
    maximum = (1 << bits) - 1
    normalized: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
            raise ValueError(f"{label} values must be integers in the range 0..{maximum}")
        normalized.append(value)
    if not normalized:
        raise ValueError("values must not be empty")
    return normalized


def _normalize_bit_value(value: object) -> int:
    if not isinstance(value, bool):
        raise ValueError("bit values must be bool")
    return int(value)


def _normalize_timer_seconds(value: object, *, name: str, allow_zero: bool) -> float:
    qualifier = "a non-negative" if allow_zero else "a positive"
    message = f"{name} must be {qualifier} finite number no greater than {_MAX_TIMER_SECONDS} seconds"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(message)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(message)
    if (value < 0 if allow_zero else value <= 0) or value > _MAX_TIMER_SECONDS:
        raise ValueError(message)
    return float(value)


def _normalize_ipv4_host(host: object, *, name: str = "host") -> str:
    if not isinstance(host, str):
        raise ValueError(f"{name} must be a string")
    if not host.strip():
        raise ValueError(f"{name} must not be empty")
    normalized = host.strip()
    literal_text = normalized[1:-1] if normalized.startswith("[") and normalized.endswith("]") else normalized
    try:
        literal = ip_address(literal_text)
    except ValueError:
        return normalized
    if literal.version != 4:
        raise ValueError(f"{name} must be an IPv4 address or a hostname that resolves to IPv4")
    return literal_text


def _resolve_ipv4_endpoint(host: str, port: int, socket_type: int) -> tuple[str, int]:
    try:
        literal = ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if literal.version != 4:
            raise socket.gaierror(f"host did not resolve to an IPv4 address: {host}")
        return str(literal), port

    endpoints = socket.getaddrinfo(host, port, socket.AF_INET, socket_type)
    for family, resolved_type, _protocol, _canonical_name, sockaddr in endpoints:
        if family == socket.AF_INET and resolved_type == socket_type:
            address, resolved_port = sockaddr[0], sockaddr[1]
            if isinstance(address, str) and isinstance(resolved_port, int):
                return address, resolved_port
    raise socket.gaierror(f"host did not resolve to an IPv4 address: {host}")


def _close_connection_socket(sock: socket.socket | None) -> None:
    if sock is None:
        return
    try:
        sock.close()
    except OSError:
        pass


def _open_ipv4_connection(
    host: str,
    port: int,
    transport: str,
    local_port: int,
    deadline: float,
    abandoned: Event,
) -> socket.socket:
    """Resolve, open, and configure one candidate without touching client state."""

    sock: socket.socket | None = None
    try:
        socket_type = socket.SOCK_STREAM if transport == "tcp" else socket.SOCK_DGRAM
        endpoint = _resolve_ipv4_endpoint(host, port, socket_type)
        if abandoned.is_set():
            raise ToyopucCancelledError("Connection attempt was abandoned")
        _remaining_time(deadline, "Connect timeout")
        if transport == "tcp":
            sock = socket.create_connection(endpoint, _remaining_time(deadline, "Connect timeout"))
            _remaining_time(deadline, "Connect timeout")
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(_remaining_time(deadline, "Connect timeout"))
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(_remaining_time(deadline, "Connect timeout"))
            sock.bind(("", local_port))
            _remaining_time(deadline, "Connect timeout")
            sock.connect(endpoint)
            sock.settimeout(_remaining_time(deadline, "Connect timeout"))
        _remaining_time(deadline, "Connect timeout")
        return sock
    except Exception:
        _close_connection_socket(sock)
        raise


def _publish_connection_attempt(
    host: str,
    port: int,
    transport: str,
    local_port: int,
    deadline: float,
    result_queue: Queue[tuple[socket.socket | None, Exception | None]],
    abandoned: Event,
    handoff_lock: LockType,
) -> None:
    candidate: socket.socket | None = None
    error: Exception | None = None
    try:
        candidate = _open_ipv4_connection(host, port, transport, local_port, deadline, abandoned)
    except Exception as exc:
        error = exc

    with handoff_lock:
        if abandoned.is_set():
            _close_connection_socket(candidate)
            return
        result_queue.put_nowait((candidate, error))


def _connection_attempt_before_deadline(
    host: str,
    port: int,
    transport: str,
    local_port: int,
    deadline: float,
    cancellation_check: Callable[[], None],
) -> socket.socket:
    """Bound an uncancellable platform resolver/socket call and reject late output."""

    result_queue: Queue[tuple[socket.socket | None, Exception | None]] = Queue(maxsize=1)
    abandoned = Event()
    handoff_lock = Lock()
    worker = Thread(
        target=_publish_connection_attempt,
        args=(host, port, transport, local_port, deadline, result_queue, abandoned, handoff_lock),
        name="ToyopucConnect",
        daemon=True,
    )
    worker.start()

    received_socket: socket.socket | None = None
    try:
        while True:
            cancellation_check()
            remaining = _remaining_time(deadline, "Connect timeout")
            try:
                received_socket, error = result_queue.get(timeout=min(remaining, 0.05))
                break
            except Empty:
                continue
        cancellation_check()
        _remaining_time(deadline, "Connect timeout")
        if error is not None:
            raise error
        if received_socket is None:
            raise OSError("Connection attempt returned no socket")
        connected = received_socket
        received_socket = None
        return connected
    except BaseException:
        _close_connection_socket(received_socket)
        with handoff_lock:
            abandoned.set()
            try:
                queued_socket, _queued_error = result_queue.get_nowait()
            except Empty:
                pass
            else:
                _close_connection_socket(queued_socket)
        raise


def _normalize_word_values(values: Iterable[int]) -> list[int]:
    return _normalize_unsigned_values(values, bits=16, label="word")


def _normalize_byte_values(values: Iterable[int]) -> list[int]:
    return _normalize_unsigned_values(values, bits=8, label="byte")


def _unpack_uint32_low_word_first_words(words: Iterable[int]) -> list[int]:
    items = [int(word) & 0xFFFF for word in words]
    if len(items) % 2 != 0:
        raise ValueError("word count must be even")
    values: list[int] = []
    for i in range(0, len(items), 2):
        values.append(items[i] | (items[i + 1] << 16))
    return values


def _pack_uint32_low_word_first_words(values: Iterable[int]) -> list[int]:
    words: list[int] = []
    for bits in _normalize_unsigned_values(values, bits=32, label="dword"):
        words.append(bits & 0xFFFF)
        words.append((bits >> 16) & 0xFFFF)
    return words


def _unpack_float32_low_word_first_words(words: Iterable[int]) -> list[float]:
    values: list[float] = []
    for bits in _unpack_uint32_low_word_first_words(words):
        value = struct.unpack("<f", struct.pack("<I", bits))[0]
        if not math.isfinite(value):
            raise ToyopucProtocolError("PLC returned a non-finite float32 value")
        values.append(value)
    return values


def _pack_float32_low_word_first_words(values: Iterable[float]) -> list[int]:
    words: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("float32 values must be finite numbers")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("float32 values must be finite numbers")
        try:
            packed = struct.pack("<f", numeric)
        except OverflowError as exc:
            raise ValueError("float32 value is outside the finite representable range") from exc
        decoded = struct.unpack("<f", packed)[0]
        if not math.isfinite(decoded):
            raise ValueError("float32 value is outside the finite representable range")
        bits = struct.unpack("<I", packed)[0]
        words.append(bits & 0xFFFF)
        words.append((bits >> 16) & 0xFFFF)
    if not words:
        raise ValueError("values must not be empty")
    return words


def format_response_error(resp: ResponseFrame) -> str:
    """Return a human-readable description for a non-OK response frame."""

    msg = f"Response error rc=0x{resp.rc:02X}"
    if resp.rc == 0x10:
        # Some PLCs return the detailed error code in CMD with no data,
        # e.g. `80 10 01 00 40`. Others may carry it in the response data.
        err = resp.data[-1] if resp.data else resp.cmd
        detail = ERROR_CODE_DESCRIPTIONS.get(err, "Unknown error code")
        return f"{msg}, error_code=0x{err:02X} ({detail}), data={resp.data.hex()}"
    return f"{msg}, data={resp.data.hex()}"


def _response_error_code(resp: ResponseFrame) -> int | None:
    if resp.rc != 0x10:
        return None
    return resp.data[-1] if resp.data else resp.cmd


def _is_read_only_payload(payload: bytes) -> bool:
    try:
        request = _parse_relay_inner_request(payload)
    except ValueError:
        return False
    return _is_read_only_request(request)


def _is_read_only_request(request: _RelayInnerRequest) -> bool:
    command = request.command
    body = request.body
    if command in {0x1C, 0x1E, 0x20, 0x22, 0x24, 0x94, 0x96, 0x98, 0xA0, 0xC2, 0xC4}:
        return True
    return command == 0x32 and body[:2] in {bytes([0x70, 0x00]), bytes([0x11, 0x00])}


def _expected_state_response_data(payload: bytes) -> bytes | None:
    try:
        request = _parse_relay_inner_request(payload)
    except ValueError:
        return None
    return _expected_state_response_data_request(request)


def _expected_state_response_data_request(request: _RelayInnerRequest) -> bytes | None:
    command = request.command
    body = request.body
    if command in _EMPTY_STATE_RESPONSE_COMMANDS:
        return b""
    if command == 0x32 and body[:2] in {
        bytes([0x71, 0x00]),
        bytes([0x01, 0x00]),
        bytes([0x02, 0x00]),
    }:
        return body[:2]
    return None


def _expected_read_response_size(payload: bytes) -> int | None:
    request = _parse_relay_inner_request(payload)
    return _expected_read_response_size_request(request)


def _expected_read_response_size_request(request: _RelayInnerRequest) -> int | None:
    command = request.command
    body = request.body

    def u16(offset: int) -> int:
        if offset < 0 or offset + 2 > len(body):
            raise ValueError("request body is too short to derive its response size")
        return body[offset] | (body[offset + 1] << 8)

    if command == 0x1C:
        return u16(2) * 2
    if command == 0x1E:
        return u16(2)
    if command == 0x20:
        return 1
    if command == 0x22:
        return len(body)
    if command == 0x24:
        return len(body) // 2
    if command == 0x94:
        return u16(3) * 2
    if command == 0x96:
        return u16(3)
    if command == 0x98:
        if len(body) < 3:
            raise ValueError("extended multi-read request body is too short")
        return ((body[0] + 7) // 8) + body[1] + body[2] * 2
    if command == 0xC2:
        return u16(4)
    if command == 0xC4:
        if len(body) < 4:
            raise ValueError("PC10 multi-read request body is too short")
        return 4 + ((body[0] + 7) // 8) + body[1] + body[2] * 2
    return None


def _require_response_data_size(command: int, data: bytes, expected: int) -> None:
    if len(data) != expected:
        raise ToyopucProtocolError(
            f"CMD={command:02X} response data size mismatch: expected={expected}, actual={len(data)}"
        )


def _extract_response_error_code(frame: bytes | None) -> int | None:
    if not frame:
        return None
    try:
        resp = parse_response(frame)
    except Exception:
        return None
    return _response_error_code(resp)


def _extract_relay_nak_error_code(frame: bytes | None) -> int | None:
    if not frame:
        return None
    try:
        resp = parse_response(frame)
    except Exception:
        return None
    if resp.cmd != 0x60:
        return None
    current = resp
    while current.cmd == 0x60:
        if len(current.data) < 4:
            return None
        ack = current.data[3]
        inner_raw = current.data[4:]
        if ack != 0x06:
            if len(inner_raw) < 3:
                return None
            inner_length = inner_raw[0] | (inner_raw[1] << 8)
            if inner_length < 1 or len(inner_raw) < 2 + inner_length:
                return None
            return inner_raw[2]
        try:
            current, _padding = parse_relay_inner_response(inner_raw)
        except Exception:
            return None
    return None


class ToyopucClient:
    """Low-level TOYOPUC computer-link client.

    Use this class when you want explicit control over command families,
    numeric addresses, and transport settings. For string-address driven use,
    prefer `ToyopucDeviceClient`. TCP and UDP connections are IPv4-only.
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        transport: str,
        local_port: int = 0,
        timeout: float = 3.0,
        retries: int = 0,
        retry_delay: float = 0.2,
    ) -> None:
        normalized_host = _normalize_ipv4_host(host)
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65_535:
            raise ValueError("port must be an integer in the range 1..65535")
        if not isinstance(transport, str) or transport.strip().lower() not in {"tcp", "udp"}:
            raise ValueError("transport must be 'tcp' or 'udp'")
        if isinstance(local_port, bool) or not isinstance(local_port, int) or not 0 <= local_port <= 65_535:
            raise ValueError("local_port must be an integer in the range 0..65535")
        normalized_transport = transport.strip().lower()
        if normalized_transport == "tcp" and local_port != 0:
            raise ValueError("local_port is only valid when transport='udp'")
        normalized_timeout = _normalize_timer_seconds(timeout, name="timeout", allow_zero=False)
        if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
            raise ValueError("retries must be a non-negative integer")
        normalized_retry_delay = _normalize_timer_seconds(retry_delay, name="retry_delay", allow_zero=True)

        self.host = normalized_host
        self.port = port
        self.local_port = local_port
        self.transport = normalized_transport
        self.timeout = normalized_timeout
        self.retries = retries
        self.retry_delay = normalized_retry_delay
        self._sock: socket.socket | None = None
        self._last_tx: bytes | None = None
        self._last_rx: bytes | None = None
        self._relay_hops_cache: dict[str, tuple[tuple[int, int], ...]] = {}
        self._maintainer_trace_hook: Callable[[ToyopucTraceFrame], None] | None = None
        self._trace_queue: Queue[tuple[Callable[[ToyopucTraceFrame], None], ToyopucTraceFrame]] | None = None
        self._operation_condition = Condition(RLock())
        self._operation_queue: deque[_OperationAdmission] = deque()
        self._operation_context = local()
        self._transport_generation = 0
        self._fixed_udp_session_tainted = False
        self._request_count = 0
        self._tx_bytes = 0
        self._rx_bytes = 0

    def traffic_stats(self) -> ToyopucTrafficStats:
        """Return an immutable lifetime traffic-counter snapshot."""
        return ToyopucTrafficStats(self._request_count, self._tx_bytes, self._rx_bytes)

    def __enter__(self) -> ToyopucClient:
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def connect(self) -> None:
        """Open TCP or UDP within one absolute DNS-through-adoption deadline."""

        with self._operation_turn():
            self._connect(time.monotonic() + self._operation_timeout())

    def _connect(self, deadline: float) -> None:
        """Open a socket within an already admitted operation."""

        if self._sock:
            return
        if self._fixed_udp_session_tainted:
            raise ToyopucNotConnectedError(
                "This fixed-port UDP session cannot be reused after an uncertain request; "
                "create a new client only after late responses can no longer be present"
            )
        attempt = 0
        while attempt <= self.retries:
            attempt += 1
            self._raise_if_cancelled()
            sock: socket.socket | None = None
            try:
                sock = _connection_attempt_before_deadline(
                    self.host,
                    self.port,
                    self.transport,
                    self.local_port,
                    deadline,
                    self._raise_if_cancelled,
                )
                with self._operation_condition:
                    self._raise_if_cancelled()
                    _remaining_time(deadline, "Connect timeout")
                    self._sock = sock
                    sock = None
                return
            except ToyopucTimeoutError as exc:
                _close_connection_socket(sock)
                if attempt <= self.retries:
                    try:
                        self._wait_retry_delay(deadline)
                    except ToyopucTimeoutError as deadline_exc:
                        raise ToyopucTimeoutError("Connect timeout") from deadline_exc
                    continue
                raise ToyopucTimeoutError("Connect timeout") from exc
            except OSError as exc:
                _close_connection_socket(sock)
                if attempt <= self.retries:
                    try:
                        self._wait_retry_delay(deadline)
                    except ToyopucTimeoutError as deadline_exc:
                        raise ToyopucTimeoutError("Connect timeout") from deadline_exc
                    continue
                raise ToyopucTransportError("Socket connection failed") from exc
            except (ToyopucCancelledError, ToyopucClosedError):
                _close_connection_socket(sock)
                raise

    def close(self) -> None:
        """Interrupt active work and retire all operations admitted before this call."""

        with self._operation_condition:
            self._transport_generation += 1
            self._operation_condition.notify_all()
        self._retire_transport()

    def _retire_transport(self) -> None:
        """Close only the transport without invalidating later queued operations."""

        if self._sock:
            try:
                if self.transport == "tcp" and hasattr(self._sock, "shutdown"):
                    try:
                        self._sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                self._sock.close()
            finally:
                self._sock = None
        self._last_tx = None
        self._last_rx = None

    def _capture_operation_admission(self) -> tuple[int, float]:
        """Capture queue-visible client settings when an async call is admitted."""

        with self._operation_condition:
            return self._transport_generation, self.timeout

    def _begin_operation_cancel_scope(
        self,
        cancel_event: Event,
        generation: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self._operation_context.cancel_event = cancel_event
        self._operation_context.admitted_generation = generation
        self._operation_context.admitted_timeout = timeout

    def _end_operation_cancel_scope(self, cancel_event: Event) -> None:
        if getattr(self._operation_context, "cancel_event", None) is cancel_event:
            self._operation_context.cancel_event = None
            self._operation_context.admitted_generation = None
            self._operation_context.admitted_timeout = None
        if self._sock is not None and self._sock.fileno() < 0:
            self._sock = None

    def _cancel_pending_operation(self, cancel_event: Event) -> None:
        cancel_event.set()
        with self._operation_condition:
            self._operation_condition.notify_all()
        sock = self._sock
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def _operation_cancel_event(self) -> Event:
        event = getattr(self._operation_context, "cancel_event", None)
        return event if isinstance(event, Event) else Event()

    @property
    def _cancel_event(self) -> Event:
        """Compatibility view of the current worker's private cancellation scope."""

        return self._operation_cancel_event()

    def _operation_timeout(self) -> float:
        timeout = getattr(self._operation_context, "active_timeout", None)
        return float(timeout) if timeout is not None else self.timeout

    def _operation_generation(self) -> int:
        generation = getattr(self._operation_context, "active_generation", None)
        if generation is None:
            with self._operation_condition:
                return self._transport_generation
        return int(generation)

    def _raise_if_cancelled(self) -> None:
        with self._operation_condition:
            if self._operation_generation() != self._transport_generation:
                raise ToyopucClosedError("Operation was retired by close()")
        if self._operation_cancel_event().is_set():
            raise ToyopucCancelledError("Operation cancelled")

    @contextmanager
    def _operation_turn(self) -> Iterator[None]:
        """Serialize transport use in FIFO order and retain nested calls in one turn."""

        depth = int(getattr(self._operation_context, "depth", 0))
        if depth:
            self._operation_context.depth = depth + 1
            try:
                self._raise_if_cancelled()
                yield
            finally:
                self._operation_context.depth -= 1
            return

        with self._operation_condition:
            captured_generation = getattr(self._operation_context, "admitted_generation", None)
            captured_timeout = getattr(self._operation_context, "admitted_timeout", None)
            admission = _OperationAdmission(
                generation=self._transport_generation if captured_generation is None else int(captured_generation),
                timeout=self.timeout if captured_timeout is None else float(captured_timeout),
                cancel_event=self._operation_cancel_event(),
            )
            self._operation_queue.append(admission)
            while self._operation_queue[0] is not admission:
                if admission.cancel_event.is_set() or admission.generation != self._transport_generation:
                    self._operation_queue.remove(admission)
                    self._operation_condition.notify_all()
                    if admission.cancel_event.is_set():
                        raise ToyopucCancelledError("Operation cancelled while waiting for the client queue")
                    raise ToyopucClosedError("Queued operation was retired by close()")
                self._operation_condition.wait()
            if admission.cancel_event.is_set() or admission.generation != self._transport_generation:
                self._operation_queue.popleft()
                self._operation_condition.notify_all()
                if admission.cancel_event.is_set():
                    raise ToyopucCancelledError("Operation cancelled before transport use")
                raise ToyopucClosedError("Queued operation was retired by close()")
            self._operation_context.depth = 1
            self._operation_context.active_generation = admission.generation
            self._operation_context.active_timeout = admission.timeout
        try:
            yield
        finally:
            self._operation_context.depth = 0
            self._operation_context.active_generation = None
            self._operation_context.active_timeout = None
            with self._operation_condition:
                if self._operation_queue and self._operation_queue[0] is admission:
                    self._operation_queue.popleft()
                elif admission in self._operation_queue:
                    self._operation_queue.remove(admission)
                self._operation_condition.notify_all()

    def _wait_retry_delay(self, deadline: float) -> None:
        delay = min(self.retry_delay, _remaining_time(deadline, "Transaction timeout during retry delay"))
        if self._operation_cancel_event().wait(delay):
            raise ToyopucCancelledError("Operation cancelled")
        _remaining_time(deadline, "Transaction timeout during retry delay")

    @staticmethod
    def _run_trace_queue(
        trace_queue: Queue[tuple[Callable[[ToyopucTraceFrame], None], ToyopucTraceFrame]],
    ) -> None:
        while True:
            hook, frame = trace_queue.get()
            try:
                hook(frame)
            except Exception:
                pass
            finally:
                trace_queue.task_done()

    def _fire_trace(self, direction: ToyopucTraceDirection, data: bytes) -> None:
        hook = self._maintainer_trace_hook
        if hook is None:
            return
        trace_queue = self._trace_queue
        if trace_queue is None:
            trace_queue = Queue(maxsize=1024)
            self._trace_queue = trace_queue
            Thread(
                target=self._run_trace_queue,
                args=(trace_queue,),
                name=f"{type(self).__name__}-trace",
                daemon=True,
            ).start()
        frame = ToyopucTraceFrame(direction, bytes(data), datetime.now(timezone.utc))
        try:
            trace_queue.put_nowait((hook, frame))
        except Full:
            # Diagnostics must never block transport; saturated traces are dropped.
            pass

    @property
    def last_tx(self) -> bytes | None:
        """Last raw frame transmitted by this client, if available."""

        return self._last_tx

    @property
    def last_rx(self) -> bytes | None:
        """Last raw frame received by this client, if available."""

        return self._last_rx

    def _recv_exact_into(self, buffer: bytearray | memoryview, deadline: float) -> None:
        assert self._sock is not None
        view = memoryview(buffer)
        offset = 0
        remaining = len(view)
        while remaining > 0:
            try:
                self._sock.settimeout(_remaining_time(deadline, "Receive timeout"))
                received = self._sock.recv_into(view[offset:], remaining)
            except TimeoutError as e:
                raise ToyopucTimeoutError("Receive timeout") from e
            if received <= 0:
                raise ConnectionResetError("Connection closed while receiving")
            self._raise_if_cancelled()
            offset += received
            remaining -= received

    def _recv_exact(self, n: int, deadline: float) -> bytes:
        buffer = bytearray(n)
        self._recv_exact_into(buffer, deadline)
        return bytes(buffer)

    def _send_and_recv(
        self,
        payload: bytes,
        *,
        state_changing: bool = False,
    ) -> ResponseFrame:
        with self._operation_turn():
            return cast(
                ResponseFrame,
                self._send_and_recv_admitted(payload, state_changing=state_changing, decode=None),
            )

    def _send_and_decode(
        self,
        payload: bytes,
        decode: Callable[[ResponseFrame], _T],
        *,
        state_changing: bool = False,
    ) -> _T:
        with self._operation_turn():
            return cast(
                _T,
                self._send_and_recv_admitted(
                    payload,
                    state_changing=state_changing,
                    decode=decode,
                ),
            )

    def _decode_post_send_result(self, decode: Callable[[], _T]) -> _T:
        """Decode after send while the caller retains the originating operation turn."""

        return self._run_post_send_decode(decode, state_changing=False)

    def _run_post_send_decode(
        self,
        decode: Callable[[], _T],
        *,
        state_changing: bool,
        failure_message: str = "Command-specific response decode failed",
    ) -> _T:
        """Apply the one transport-retirement boundary to every post-send decoder."""

        try:
            return decode()
        except ToyopucProtocolError as exc:
            self._raise_post_send_protocol_error(exc, state_changing=state_changing)
        except ToyopucError:
            raise
        except Exception as exc:
            error = ToyopucProtocolError(failure_message)
            error.__cause__ = exc
            self._raise_post_send_protocol_error(error, state_changing=state_changing)
        raise AssertionError("unreachable response decode path")

    def _send_and_recv_admitted(
        self,
        payload: bytes,
        *,
        state_changing: bool,
        decode: Callable[[ResponseFrame], object] | None,
    ) -> object:
        request = _parse_relay_inner_request(payload)
        expected_read_size = None if state_changing else _expected_read_response_size_request(request)
        deadline = time.monotonic() + self._operation_timeout()
        self._raise_if_cancelled()
        if not self._sock:
            self._connect(deadline)
        assert self._sock is not None
        self._last_tx = payload
        self._last_rx = None
        self._fire_trace(ToyopucTraceDirection.SEND, payload)
        request_may_have_been_sent = False

        try:
            self._sock.settimeout(_remaining_time(deadline, "Send timeout"))
            self._raise_if_cancelled()
            request_may_have_been_sent = True
            if self.transport == "tcp":
                self._sock.sendall(payload)
                self._request_count += 1
                self._tx_bytes += len(payload)
                header = bytearray(4)
                self._recv_exact_into(header, deadline)
                ll, lh = header[2], header[3]
                length = ll | (lh << 8)
                frame_buffer = bytearray(4 + length)
                frame_buffer[:4] = header
                self._recv_exact_into(memoryview(frame_buffer)[4:], deadline)
                frame = bytes(frame_buffer)
            else:
                if self._sock.send(payload) != len(payload):
                    raise OSError("UDP send did not accept the complete TOYOPUC datagram")
                self._request_count += 1
                self._tx_bytes += len(payload)
                self._sock.settimeout(_remaining_time(deadline, "UDP receive timeout"))
                frame = self._sock.recv(UDP_RECEIVE_BUFFER_SIZE)
                self._raise_if_cancelled()
            _remaining_time(deadline, "Response decode timeout")
            self._rx_bytes += len(frame)
        except (TimeoutError, ToyopucTimeoutError) as exc:
            if request_may_have_been_sent and self.transport == "udp" and self.local_port != 0:
                self._fixed_udp_session_tainted = True
            with self._operation_condition:
                closed = self._operation_generation() != self._transport_generation
            cancelled = self._operation_cancel_event().is_set()
            if closed:
                reason = ToyopucOutcomeUnknownReason.CLOSED
                timeout_error: Exception = ToyopucClosedError("Operation was interrupted by close()")
            elif cancelled:
                reason = ToyopucOutcomeUnknownReason.CANCELLATION
                timeout_error = ToyopucCancelledError("Operation cancelled")
            else:
                reason = ToyopucOutcomeUnknownReason.TIMEOUT
                timeout_error = ToyopucTimeoutError("Send/receive timeout")
            self._retire_transport()
            if state_changing and request_may_have_been_sent:
                cause = _native_cause(exc)
                raise ToyopucOperationOutcomeUnknownError(
                    reason,
                    "State-changing request may have reached the PLC before the timeout",
                    cause=cause,
                ) from cause
            raise timeout_error from exc
        except (OSError, ToyopucCancelledError, ToyopucClosedError) as exc:
            if request_may_have_been_sent and self.transport == "udp" and self.local_port != 0:
                self._fixed_udp_session_tainted = True
            with self._operation_condition:
                closed = self._operation_generation() != self._transport_generation
            cancelled = self._operation_cancel_event().is_set()
            if closed:
                reason = ToyopucOutcomeUnknownReason.CLOSED
                transport_error: Exception = ToyopucClosedError("Operation was interrupted by close()")
            elif cancelled or isinstance(exc, ToyopucCancelledError):
                reason = ToyopucOutcomeUnknownReason.CANCELLATION
                transport_error = ToyopucCancelledError("Operation cancelled")
            else:
                reason = ToyopucOutcomeUnknownReason.TRANSPORT
                transport_error = ToyopucTransportError("Socket error")
            self._retire_transport()
            if state_changing and request_may_have_been_sent:
                cause = _native_cause(exc)
                raise ToyopucOperationOutcomeUnknownError(
                    reason,
                    "State-changing request may have reached the PLC before the transport failed",
                    cause=cause,
                ) from cause
            raise transport_error from exc

        def validate_and_decode() -> object:
            self._fire_trace(ToyopucTraceDirection.RECEIVE, frame)
            self._last_rx = frame
            resp = parse_response(frame)
            _remaining_time(deadline, "Response decode timeout")
            if resp.ft != FT_RESPONSE:
                raise ToyopucProtocolError(f"Unexpected frame type: 0x{resp.ft:02X}")
            if resp.rc != 0x00 and resp.data and resp.cmd != request.command:
                raise ToyopucProtocolError(
                    "Unexpected data-bearing error response command: "
                    f"expected 0x{request.command:02X}, got 0x{resp.cmd:02X}"
                )
            if resp.rc != 0x00:
                raise ToyopucPlcError(format_response_error(resp))
            if resp.cmd != request.command:
                raise ToyopucProtocolError(
                    f"Unexpected response command: expected 0x{request.command:02X}, got 0x{resp.cmd:02X}"
                )
            expected_state_data = _expected_state_response_data_request(request) if state_changing else None
            if expected_state_data is not None and resp.data != expected_state_data:
                raise ToyopucProtocolError(
                    "State-changing response data mismatch: "
                    f"expected={expected_state_data.hex()}, actual={resp.data.hex()}"
                )
            if expected_read_size is not None:
                _require_response_data_size(request.command, resp.data, expected_read_size)
            if decode is None:
                return resp
            return decode(resp)

        return self._run_post_send_decode(validate_and_decode, state_changing=state_changing)

    def _raise_post_send_protocol_error(
        self,
        error: ToyopucProtocolError,
        *,
        state_changing: bool,
    ) -> None:
        if self.transport == "udp" and self.local_port != 0:
            self._fixed_udp_session_tainted = True
        self._retire_transport()
        if state_changing:
            raise ToyopucOperationOutcomeUnknownError(
                ToyopucOutcomeUnknownReason.MALFORMED_RESPONSE,
                "State-changing request may have reached the PLC, but its response was not valid",
                cause=error,
            ) from error
        raise error

    def _send_raw(self, cmd: int, data: bytes) -> ResponseFrame:
        """Maintainer-only raw command path."""

        payload = build_command(cmd, data)
        return self._send_and_recv(payload, state_changing=True)

    def _send_payload(self, payload: bytes) -> ResponseFrame:
        """Maintainer-only prebuilt-payload path."""
        return self._send_and_recv(payload, state_changing=True)

    def read_words(self, addr: int, count: int) -> list[int]:
        """Read one or more basic-area words with `CMD=1C`."""
        return self._send_and_decode(
            build_word_read(addr, count),
            lambda response: unpack_u16_le(response.data),
        )

    def write_words(self, addr: int, values: Iterable[int]) -> None:
        """Write one or more basic-area words with `CMD=1D`."""
        self._send_and_recv(build_word_write(addr, values), state_changing=True)

    def read_bytes(self, addr: int, count: int) -> bytes:
        """Read one or more basic-area bytes with `CMD=1E`."""
        return self._send_and_decode(build_byte_read(addr, count), lambda response: response.data)

    def write_bytes(self, addr: int, values: Iterable[int]) -> None:
        """Write one or more basic-area bytes with `CMD=1F`."""
        self._send_and_recv(build_byte_write(addr, values), state_changing=True)

    def read_bit(self, addr: int) -> bool:
        """Read one basic-area bit with `CMD=20`."""
        return self._send_and_decode(build_bit_read(addr), lambda response: response.data[0] != 0)

    def write_bit(self, addr: int, value: bool) -> None:
        """Write one basic-area bit with `CMD=21`; *value* must be `bool`."""
        self._send_and_recv(build_bit_write(addr, _normalize_bit_value(value)), state_changing=True)

    def read_dword(self, addr: int) -> int:
        """Read one 32-bit value from two consecutive words."""
        with self._operation_turn():
            values = self.read_dwords(addr, 1)
            return self._decode_post_send_result(lambda: values[0])

    def write_dword(self, addr: int, value: int) -> None:
        """Write one 32-bit value to two consecutive words."""
        self.write_dwords(addr, [value])

    def read_dwords(self, addr: int, count: int) -> list[int]:
        """Read one or more 32-bit values from consecutive words."""
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError("count must be an integer >= 1")
        with self._operation_turn():
            words = self.read_words(addr, count * 2)
            return self._decode_post_send_result(lambda: _unpack_uint32_low_word_first_words(words))

    def write_dwords(self, addr: int, values: Iterable[int]) -> None:
        """Write one or more 32-bit values to consecutive words."""
        self.write_words(addr, _pack_uint32_low_word_first_words(values))

    def read_float32(self, addr: int) -> float:
        """Read one IEEE-754 float32 from two consecutive words."""
        with self._operation_turn():
            values = self.read_float32s(addr, 1)
            return self._decode_post_send_result(lambda: values[0])

    def write_float32(self, addr: int, value: float) -> None:
        """Write one IEEE-754 float32 to two consecutive words."""
        self.write_float32s(addr, [value])

    def read_float32s(self, addr: int, count: int) -> list[float]:
        """Read one or more IEEE-754 float32 values from consecutive words."""
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError("count must be an integer >= 1")
        with self._operation_turn():
            words = self.read_words(addr, count * 2)
            return self._decode_post_send_result(lambda: _unpack_float32_low_word_first_words(words))

    def write_float32s(self, addr: int, values: Iterable[float]) -> None:
        """Write one or more IEEE-754 float32 values to consecutive words."""
        self.write_words(addr, _pack_float32_low_word_first_words(values))

    def read_words_multi(self, addrs: Iterable[int]) -> list[int]:
        """Read multiple non-contiguous basic-area words with `CMD=22`."""
        address_list = list(addrs)
        return self._send_and_decode(
            build_multi_word_read(address_list),
            lambda response: unpack_u16_le(response.data),
        )

    def write_words_multi(self, pairs: Iterable[tuple[int, int]]) -> None:
        """Write multiple non-contiguous basic-area words with `CMD=23`."""
        self._send_and_recv(build_multi_word_write(pairs), state_changing=True)

    def read_bytes_multi(self, addrs: Iterable[int]) -> bytes:
        """Read multiple non-contiguous basic-area bytes with `CMD=24`."""
        address_list = list(addrs)
        return self._send_and_decode(
            build_multi_byte_read(address_list),
            lambda response: response.data,
        )

    def write_bytes_multi(self, pairs: Iterable[tuple[int, int]]) -> None:
        """Write multiple non-contiguous basic-area bytes with `CMD=25`."""
        self._send_and_recv(build_multi_byte_write(pairs), state_changing=True)

    def read_ext_words(self, no: int, addr: int, count: int) -> list[int]:
        """Read extended-area words with `CMD=94` using `(No., addr)`."""
        return self._send_and_decode(
            build_ext_word_read(no, addr, count),
            lambda response: unpack_u16_le(response.data),
        )

    def write_ext_words(self, no: int, addr: int, values: Iterable[int]) -> None:
        """Write extended-area words with `CMD=95` using `(No., addr)`."""
        self._send_and_recv(build_ext_word_write(no, addr, values), state_changing=True)

    def read_ext_bytes(self, no: int, addr: int, count: int) -> bytes:
        """Read extended-area bytes with `CMD=96` using `(No., addr)`."""
        return self._send_and_decode(
            build_ext_byte_read(no, addr, count),
            lambda response: response.data,
        )

    def write_ext_bytes(self, no: int, addr: int, values: Iterable[int]) -> None:
        """Write extended-area bytes with `CMD=97` using `(No., addr)`."""
        self._send_and_recv(build_ext_byte_write(no, addr, values), state_changing=True)

    def read_ext_multi(
        self,
        bit_points: Iterable[tuple[int, int, int]],
        byte_points: Iterable[tuple[int, int]],
        word_points: Iterable[tuple[int, int]],
    ) -> bytes:
        """Read mixed extended points with `CMD=98`.

        `bit_points` items are `(no, bit_no, addr)`.
        `byte_points` items are `(no, addr)`.
        `word_points` items are `(no, addr)`.

        All `addr` fields are monitor byte addresses, including `word_points`
        (manual: "byte address N"). A `CMD=94` word address must be doubled
        before it is used as a `word_points` address.
        """
        bits = list(bit_points)
        bytes_ = list(byte_points)
        words = list(word_points)
        return self._send_and_decode(
            build_ext_multi_read(bits, bytes_, words),
            lambda response: response.data,
        )

    def write_ext_multi(
        self,
        bit_points: Iterable[tuple[int, int, int, bool]],
        byte_points: Iterable[tuple[int, int, int]],
        word_points: Iterable[tuple[int, int, int]],
    ) -> None:
        """Write mixed extended points with `CMD=99`.

        All `addr` fields are monitor byte addresses, including `word_points`
        (manual: "byte address N"), as in :meth:`read_ext_multi`. Each bit
        point value must be an actual `bool`.
        """
        bits = [(no, bit_no, addr, _normalize_bit_value(value)) for no, bit_no, addr, value in bit_points]
        self._send_and_recv(build_ext_multi_write(bits, list(byte_points), list(word_points)), state_changing=True)

    def pc10_block_read(self, addr32: int, count: int) -> bytes:
        """Read PC10 block data with `CMD=C2` from a 32-bit byte address."""
        return self._send_and_decode(
            build_pc10_block_read(addr32, count),
            lambda response: response.data,
        )

    def pc10_block_write(self, addr32: int, data_bytes: bytes) -> None:
        """Write PC10 block data with `CMD=C3` to a 32-bit byte address."""
        self._send_and_recv(build_pc10_block_write(addr32, data_bytes), state_changing=True)

    def pc10_multi_read(self, payload: bytes) -> bytes:
        """Read PC10 multi-point data with `CMD=C4` using a prebuilt payload."""
        return self._send_and_decode(
            build_pc10_multi_read(payload),
            lambda response: response.data,
        )

    def pc10_multi_write(self, payload: bytes) -> None:
        """Write PC10 multi-point data with `CMD=C5` using a prebuilt payload."""
        self._send_and_recv(build_pc10_multi_write(payload), state_changing=True)

    def read_fr_words(self, index: int, count: int) -> list[int]:
        """Read FR words via exactly one PC10 block-read request (`CMD=C2`).

        `FR` real-hardware access uses 32-bit PC10 addressing with
        `Ex No.=0x40-0x7F`, not `CMD=94`.
        """
        start, word_count = _validate_fr_single_request(index, count)
        return self._send_and_decode(
            build_pc10_block_read(encode_fr_word_addr32(start), word_count * 2),
            lambda response: unpack_u16_le(response.data),
        )

    def write_fr_words(self, index: int, values: Iterable[int]) -> None:
        """Update the FR work area with exactly one PC10 block-write request.

        This method never commits flash. Call :meth:`commit_fr_block`
        separately with an explicit block-start index when persistence is
        intended.
        """
        vals = _normalize_fr_word_values(values)
        start, _ = _validate_fr_single_request(index, len(vals))
        data = b"".join(v.to_bytes(2, "little") for v in vals)
        self.pc10_block_write(encode_fr_word_addr32(start), data)

    def commit_fr_block(
        self,
        block_start_index: int,
    ) -> None:
        """Commit exactly one explicitly selected FR block with `CMD=CA`."""
        block_start = _validate_fr_block_start(block_start_index)
        self._send_and_recv(build_fr_register(fr_block_ex_no(block_start)), state_changing=True)

    def relay_command(self, link_no: int, station_no: int, inner_payload: bytes) -> ResponseFrame:
        """Wrap a command in one relay hop using `CMD=60`."""
        request = _parse_relay_inner_request(inner_payload)
        return self._send_and_recv(
            _build_relay_command_trimmed(link_no, station_no, request.trimmed_payload),
            state_changing=not _is_read_only_request(request),
        )

    def relay_nested(
        self,
        hops: Iterable[tuple[int, int]],
        inner_payload: bytes,
    ) -> ResponseFrame:
        """Wrap a command in multiple relay hops using nested `CMD=60` frames."""
        request = _parse_relay_inner_request(inner_payload)
        return self._relay_nested_request(tuple(hops), request, inner_payload)

    def _relay_nested_request(
        self,
        hops: Iterable[tuple[int, int]],
        request: _RelayInnerRequest,
        original_payload: bytes,
    ) -> ResponseFrame:
        del original_payload
        return self._send_and_recv(
            _build_relay_nested_parsed(list(hops), request),
            state_changing=not _is_read_only_request(request),
        )

    def send_via_relay(self, hops: str | Iterable[tuple[int, int]], inner_payload: bytes) -> ResponseFrame:
        """Send a command through relay hops and return the final inner response."""
        return self._send_via_relay_decoded(hops, inner_payload, lambda response: response)

    def _send_via_relay_decoded(
        self,
        hops: str | Iterable[tuple[int, int]],
        inner_payload: bytes,
        decode: Callable[[ResponseFrame], _T],
    ) -> _T:
        with self._operation_turn():
            return self._send_via_relay_decoded_admitted(hops, inner_payload, decode)

    def _send_via_relay_decoded_admitted(
        self,
        hops: str | Iterable[tuple[int, int]],
        inner_payload: bytes,
        decode: Callable[[ResponseFrame], _T],
    ) -> _T:
        request = _parse_relay_inner_request(inner_payload)
        normalized: tuple[tuple[int, int], ...]
        if isinstance(hops, str):
            cached = self._relay_hops_cache.get(hops)
            if cached is None:
                normalized = tuple(normalize_relay_hops(hops))
                if len(self._relay_hops_cache) >= 128:
                    self._relay_hops_cache.clear()
                self._relay_hops_cache[hops] = normalized
            else:
                normalized = cached
        else:
            normalized = tuple(normalize_relay_hops(hops))
        state_changing = not _is_read_only_request(request)
        outer = self._relay_nested_request(normalized, request, inner_payload)
        layers, final = self._run_post_send_decode(
            lambda: unwrap_relay_response_chain(outer),
            state_changing=state_changing,
            failure_message="Relay response unwrap failed",
        )
        if final is None:
            last = layers[-1]
            raise ToyopucProtocolError(
                f"Relay NAK at link=0x{last.link_no:02X}, station=0x{last.station_no:04X}, ack=0x{last.ack:02X}"
            )

        def validate_and_decode_relay() -> _T:
            if final.cmd != request.command:
                raise ToyopucProtocolError(
                    f"Unexpected relay response command: expected 0x{request.command:02X}, got 0x{final.cmd:02X}"
                )
            expected_state_data = _expected_state_response_data_request(request) if state_changing else None
            if expected_state_data is not None and final.data != expected_state_data:
                raise ToyopucProtocolError(
                    "Relay state-changing response data mismatch: "
                    f"expected={expected_state_data.hex()}, actual={final.data.hex()}"
                )
            if not state_changing:
                expected_read_size = _expected_read_response_size_request(request)
                if expected_read_size is not None and len(final.data) != expected_read_size:
                    raise ToyopucProtocolError(
                        f"CMD={request.command:02X} relay response data size mismatch: "
                        f"expected={expected_read_size}, actual={len(final.data)}"
                    )
            return decode(final)

        return self._run_post_send_decode(
            validate_and_decode_relay,
            state_changing=state_changing,
            failure_message="Command-specific Relay response decode failed",
        )

    def relay_read_words(self, hops: str | Iterable[tuple[int, int]], addr: int, count: int) -> list[int]:
        """Read one or more basic-area words through relay hops."""
        return self._send_via_relay_decoded(
            hops,
            build_word_read(addr, count),
            lambda response: unpack_u16_le(response.data),
        )

    def relay_write_words(self, hops: str | Iterable[tuple[int, int]], addr: int, values: Iterable[int]) -> None:
        """Write one or more basic-area words through relay hops."""
        self.send_via_relay(hops, build_word_write(addr, values))

    def relay_read_clock(self, hops: str | Iterable[tuple[int, int]]) -> ClockData:
        """Read the CPU clock through relay hops."""
        return self._send_via_relay_decoded(
            hops,
            build_clock_read(),
            lambda response: parse_clock_data(response.data),
        )

    def relay_write_clock(
        self,
        hops: str | Iterable[tuple[int, int]],
        value: datetime,
        *,
        year_base: int,
    ) -> None:
        """Set the CPU clock through relay hops via `CMD=32 / 71 00`."""
        self._validate_clock_write(value, year_base)
        weekday = (value.weekday() + 1) % 7
        self.send_via_relay(
            hops,
            build_clock_write(
                value.second,
                value.minute,
                value.hour,
                value.day,
                value.month,
                value.year - year_base,
                weekday,
            ),
        )

    def relay_resume_scan(self, hops: str | Iterable[tuple[int, int]]) -> None:
        """Resume CPU scan through relay hops via `CMD=32 / 01 00`."""
        self.send_via_relay(hops, build_scan_resume())

    def relay_stop_scan(self, hops: str | Iterable[tuple[int, int]]) -> None:
        """Stop CPU scan through relay hops via `CMD=32 / 02 00 01`."""
        self.send_via_relay(hops, build_scan_stop())

    def relay_release_scan_stop(self, hops: str | Iterable[tuple[int, int]]) -> None:
        """Release CPU scan stop through relay hops via `CMD=32 / 02 00 00`."""
        self.send_via_relay(hops, build_scan_stop_release())

    def relay_read_cpu_status(self, hops: str | Iterable[tuple[int, int]]) -> CpuStatusData:
        """Read the 8-byte CPU status block through relay hops."""
        return self._send_via_relay_decoded(
            hops,
            build_cpu_status_read(),
            lambda response: parse_cpu_status_data(response.data),
        )

    def relay_read_cpu_status_a0_raw(self, hops: str | Iterable[tuple[int, int]]) -> bytes:
        """Read raw 8-byte CPU status through relay hops via `CMD=A0 / 00 11 00`."""
        return self._send_via_relay_decoded(
            hops,
            build_cpu_status_read_a0(),
            lambda response: parse_cpu_status_data_a0_raw(response.data),
        )

    def relay_read_cpu_status_a0(self, hops: str | Iterable[tuple[int, int]]) -> CpuStatusData:
        """Read decoded CPU status through relay hops via `CMD=A0 / 00 11 00`."""
        return self._send_via_relay_decoded(
            hops,
            build_cpu_status_read_a0(),
            lambda response: parse_cpu_status_data_a0(response.data),
        )

    def relay_write_fr_words(
        self,
        hops: str | Iterable[tuple[int, int]],
        index: int,
        values: Iterable[int],
    ) -> None:
        """Update the remote FR work area with exactly one request."""
        vals = _normalize_fr_word_values(values)
        start, _ = _validate_fr_single_request(index, len(vals))
        data = b"".join(v.to_bytes(2, "little") for v in vals)
        self.send_via_relay(hops, build_pc10_block_write(encode_fr_word_addr32(start), data))

    def relay_commit_fr_block(
        self,
        hops: str | Iterable[tuple[int, int]],
        block_start_index: int,
    ) -> None:
        """Commit exactly one explicitly selected remote FR block."""
        block_start = _validate_fr_block_start(block_start_index)
        self.send_via_relay(hops, build_fr_register(fr_block_ex_no(block_start)))

    def read_clock(self) -> ClockData:
        """Read the CPU clock via `CMD=32 / 70 00`."""
        return self._send_and_decode(build_clock_read(), lambda response: parse_clock_data(response.data))

    def read_cpu_status(self) -> CpuStatusData:
        """Read the 8-byte CPU status block via `CMD=32 / 11 00`."""
        return self._send_and_decode(
            build_cpu_status_read(),
            lambda response: parse_cpu_status_data(response.data),
        )

    def read_cpu_status_a0_raw(self) -> bytes:
        """Read raw 8-byte CPU status via `CMD=A0 / 00 11 00`.

        This command path is used in the flash/FR completion flow. The library
        currently returns the 8 raw status bytes because the exact bit mapping
        for this path has not been finalized yet.
        """
        return self._send_and_decode(
            build_cpu_status_read_a0(),
            lambda response: parse_cpu_status_data_a0_raw(response.data),
        )

    def read_cpu_status_a0(self) -> CpuStatusData:
        """Read decoded CPU status via `CMD=A0 / 00 11 00`."""
        return self._send_and_decode(
            build_cpu_status_read_a0(),
            lambda response: parse_cpu_status_data_a0(response.data),
        )

    @staticmethod
    def _validate_clock_write(value: datetime, year_base: int) -> None:
        if isinstance(year_base, bool) or not isinstance(year_base, int) or year_base < 0 or year_base % 100 != 0:
            raise ValueError("year_base must be a non-negative century boundary")
        if value.tzinfo is not None and value.utcoffset() is not None:
            raise ValueError("clock write requires a timezone-naive PLC local datetime")
        if not year_base <= value.year <= year_base + 99:
            raise ValueError("clock year must be within year_base..year_base+99")

    def write_clock(self, value: datetime, *, year_base: int) -> None:
        """Set the CPU clock via `CMD=32 / 71 00`."""
        self._validate_clock_write(value, year_base)
        weekday = (value.weekday() + 1) % 7  # Python Monday=0, PLC Sunday=0
        self._send_and_recv(
            build_clock_write(
                value.second,
                value.minute,
                value.hour,
                value.day,
                value.month,
                value.year - year_base,
                weekday,
            ),
            state_changing=True,
        )

    def resume_scan(self) -> None:
        """Resume CPU scan via `CMD=32 / 01 00`."""
        self._send_and_recv(build_scan_resume(), state_changing=True)

    def stop_scan(self) -> None:
        """Stop CPU scan via `CMD=32 / 02 00 01`."""
        self._send_and_recv(build_scan_stop(), state_changing=True)

    def release_scan_stop(self) -> None:
        """Release CPU scan stop via `CMD=32 / 02 00 00`."""
        self._send_and_recv(build_scan_stop_release(), state_changing=True)


_FIFO_OPERATION_METHODS = (
    "read_words",
    "write_words",
    "read_bytes",
    "write_bytes",
    "read_bit",
    "write_bit",
    "read_dword",
    "write_dword",
    "read_dwords",
    "write_dwords",
    "read_float32",
    "write_float32",
    "read_float32s",
    "write_float32s",
    "read_words_multi",
    "write_words_multi",
    "read_bytes_multi",
    "write_bytes_multi",
    "read_ext_words",
    "write_ext_words",
    "read_ext_bytes",
    "write_ext_bytes",
    "read_ext_multi",
    "write_ext_multi",
    "pc10_block_read",
    "pc10_block_write",
    "pc10_multi_read",
    "pc10_multi_write",
    "read_fr_words",
    "write_fr_words",
    "commit_fr_block",
    "relay_command",
    "relay_nested",
    "send_via_relay",
    "relay_read_words",
    "relay_write_words",
    "relay_read_clock",
    "relay_write_clock",
    "relay_resume_scan",
    "relay_stop_scan",
    "relay_release_scan_stop",
    "relay_read_cpu_status",
    "relay_read_cpu_status_a0_raw",
    "relay_read_cpu_status_a0",
    "relay_write_fr_words",
    "relay_commit_fr_block",
    "read_clock",
    "read_cpu_status",
    "read_cpu_status_a0_raw",
    "read_cpu_status_a0",
    "write_clock",
    "resume_scan",
    "stop_scan",
    "release_scan_stop",
)


def _install_fifo_operation(method_name: str) -> None:
    method = getattr(ToyopucClient, method_name)

    @wraps(method)
    def fifo_operation(self: ToyopucClient, *args: object, **kwargs: object) -> object:
        admitted_args = tuple(_snapshot_operation_argument(argument) for argument in args)
        admitted_kwargs = {name: _snapshot_operation_argument(argument) for name, argument in kwargs.items()}
        with self._operation_turn():
            return method(self, *admitted_args, **admitted_kwargs)

    setattr(ToyopucClient, method_name, fifo_operation)


for _fifo_method_name in _FIFO_OPERATION_METHODS:
    _install_fifo_operation(_fifo_method_name)
