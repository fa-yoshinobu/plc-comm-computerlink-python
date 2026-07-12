from __future__ import annotations

import math
import socket
import struct
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from queue import Full, Queue
from threading import Event, Thread

from .address import encode_fr_word_addr32, fr_block_ex_no
from .errors import ToyopucError, ToyopucOperationOutcomeUnknownError, ToyopucProtocolError, ToyopucTimeoutError
from .protocol import (
    FT_RESPONSE,
    ClockData,
    CpuStatusData,
    ResponseFrame,
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
    build_relay_command,
    build_relay_nested,
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


_RETRYABLE_RESPONSE_ERROR_CODES = {0x73}
UDP_RECEIVE_BUFFER_SIZE = 65_535
_FR_BLOCK_WORDS = 0x8000
_FR_MAX_INDEX = 0x1FFFFF
_FR_IO_CHUNK_WORDS = 0x01F8


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
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and value in (0, 1):
        return value
    raise ValueError("bit values must be bool or integers 0 or 1")


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
        values.append(struct.unpack("<f", struct.pack("<I", bits))[0])
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


def _is_retryable_response_error(resp: ResponseFrame) -> bool:
    return _response_error_code(resp) in _RETRYABLE_RESPONSE_ERROR_CODES


def _is_read_only_payload(payload: bytes) -> bool:
    if len(payload) < 5:
        return False
    command = payload[4]
    if command in {0x1C, 0x1E, 0x20, 0x22, 0x24, 0x94, 0x96, 0x98, 0xA0, 0xC2, 0xC4}:
        return True
    return command == 0x32 and len(payload) >= 7 and payload[5:7] in {bytes([0x70, 0x00]), bytes([0x11, 0x00])}


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
    prefer `ToyopucDeviceClient`.
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
        if not isinstance(host, str) or not host.strip():
            raise ValueError("host must be a non-empty string")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65_535:
            raise ValueError("port must be an integer in the range 1..65535")
        if not isinstance(transport, str) or transport.strip().lower() not in {"tcp", "udp"}:
            raise ValueError("transport must be 'tcp' or 'udp'")
        if isinstance(local_port, bool) or not isinstance(local_port, int) or not 0 <= local_port <= 65_535:
            raise ValueError("local_port must be an integer in the range 0..65535")
        normalized_transport = transport.strip().lower()
        if normalized_transport == "tcp" and local_port != 0:
            raise ValueError("local_port is only valid when transport='udp'")
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout must be a positive finite number")
        if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
            raise ValueError("retries must be a non-negative integer")
        if (
            isinstance(retry_delay, bool)
            or not isinstance(retry_delay, (int, float))
            or not math.isfinite(retry_delay)
            or retry_delay < 0
        ):
            raise ValueError("retry_delay must be a non-negative finite number")

        self.host = host.strip()
        self.port = port
        self.local_port = local_port
        self.transport = normalized_transport
        self.timeout = float(timeout)
        self.retries = retries
        self.retry_delay = float(retry_delay)
        self._sock: socket.socket | None = None
        self._last_tx: bytes | None = None
        self._last_rx: bytes | None = None
        self._relay_hops_cache: dict[str, tuple[tuple[int, int], ...]] = {}
        self._maintainer_trace_hook: Callable[[ToyopucTraceFrame], None] | None = None
        self._trace_queue: Queue[tuple[Callable[[ToyopucTraceFrame], None], ToyopucTraceFrame]] | None = None
        self._cancel_event = Event()
        self._fixed_udp_session_tainted = False

    def __enter__(self) -> ToyopucClient:
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def connect(self) -> None:
        """Open the configured TCP or UDP socket if it is not already open."""

        if self._sock:
            return
        if self._fixed_udp_session_tainted:
            raise ToyopucError(
                "This fixed-port UDP session cannot be reused after an uncertain request; "
                "create a new client only after late responses can no longer be present"
            )
        attempt = 0
        while attempt <= self.retries:
            attempt += 1
            self._raise_if_cancelled()
            sock: socket.socket | None = None
            try:
                if self.transport == "tcp":
                    sock = socket.create_connection((self.host, self.port), self.timeout)
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                else:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.bind(("", self.local_port))
                    sock.connect((self.host, self.port))
                    sock.settimeout(self.timeout)
                self._sock = sock
                return
            except (OSError, TimeoutError) as exc:
                if sock is not None:
                    sock.close()
                if attempt <= self.retries:
                    self._wait_retry_delay()
                    continue
                raise ToyopucError("Socket connection failed") from exc

    def close(self) -> None:
        """Close the current socket and clear transport state."""

        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None
        self._last_tx = None
        self._last_rx = None

    def _cancel_pending_operation(self) -> None:
        self._cancel_event.set()
        sock = self._sock
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def _clear_operation_cancel(self) -> None:
        self._cancel_event.clear()
        if self._sock is not None and self._sock.fileno() < 0:
            self._sock = None

    def _raise_if_cancelled(self) -> None:
        if self._cancel_event.is_set():
            raise ToyopucError("Operation cancelled")

    def _wait_retry_delay(self) -> None:
        if self._cancel_event.wait(self.retry_delay):
            raise ToyopucError("Operation cancelled")

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

    def _recv_exact_into(self, buffer: bytearray | memoryview) -> None:
        assert self._sock is not None
        view = memoryview(buffer)
        offset = 0
        remaining = len(view)
        while remaining > 0:
            try:
                received = self._sock.recv_into(view[offset:], remaining)
            except TimeoutError as e:
                raise ToyopucTimeoutError("Receive timeout") from e
            if received <= 0:
                raise ToyopucProtocolError("Connection closed while receiving")
            offset += received
            remaining -= received

    def _recv_exact(self, n: int) -> bytes:
        buffer = bytearray(n)
        self._recv_exact_into(buffer)
        return bytes(buffer)

    def _send_and_recv(
        self,
        payload: bytes,
        *,
        retryable: bool = False,
        state_changing: bool = False,
    ) -> ResponseFrame:
        attempt = 0
        last_err: Exception | None = None
        allowed_retries = self.retries if retryable else 0
        while attempt <= allowed_retries:
            attempt += 1
            self._raise_if_cancelled()
            if not self._sock:
                self.connect()
            assert self._sock is not None
            self._last_tx = payload
            self._last_rx = None
            self._fire_trace(ToyopucTraceDirection.SEND, payload)
            request_may_have_been_sent = False

            try:
                request_may_have_been_sent = True
                if self.transport == "tcp":
                    self._sock.sendall(payload)
                    header = bytearray(4)
                    self._recv_exact_into(header)
                    ll, lh = header[2], header[3]
                    length = ll | (lh << 8)
                    frame_buffer = bytearray(4 + length)
                    frame_buffer[:4] = header
                    self._recv_exact_into(memoryview(frame_buffer)[4:])
                    frame = bytes(frame_buffer)
                else:
                    self._sock.send(payload)
                    frame = self._sock.recv(UDP_RECEIVE_BUFFER_SIZE)
            except (TimeoutError, ToyopucTimeoutError) as e:
                if request_may_have_been_sent and self.transport == "udp" and self.local_port != 0:
                    self._fixed_udp_session_tainted = True
                last_err = ToyopucTimeoutError("Send/receive timeout")
                if attempt <= allowed_retries and not self._fixed_udp_session_tainted:
                    try:
                        self.close()
                    except Exception:
                        pass

                    self._wait_retry_delay()
                    continue
                self.close()
                if state_changing and request_may_have_been_sent:
                    raise ToyopucOperationOutcomeUnknownError(
                        "State-changing request may have reached the PLC before the timeout"
                    ) from e
                raise last_err from e
            except OSError as e:
                if request_may_have_been_sent and self.transport == "udp" and self.local_port != 0:
                    self._fixed_udp_session_tainted = True
                last_err = ToyopucError("Socket error")
                if attempt <= allowed_retries and not self._fixed_udp_session_tainted:
                    try:
                        self.close()
                    except Exception:
                        pass

                    self._wait_retry_delay()
                    continue
                self.close()
                if state_changing and request_may_have_been_sent:
                    raise ToyopucOperationOutcomeUnknownError(
                        "State-changing request may have reached the PLC before the transport failed"
                    ) from e
                raise last_err from e

            self._fire_trace(ToyopucTraceDirection.RECEIVE, frame)
            self._last_rx = frame
            resp = parse_response(frame)
            if resp.ft != FT_RESPONSE:
                raise ToyopucProtocolError(f"Unexpected frame type: 0x{resp.ft:02X}")
            if resp.rc != 0x00:
                last_err = ToyopucError(format_response_error(resp))
                if retryable and _is_retryable_response_error(resp) and attempt <= allowed_retries:
                    self._wait_retry_delay()
                    continue
                raise last_err
            return resp

        if last_err:
            raise last_err
        raise ToyopucError("Send/receive failed")

    def _send_raw(self, cmd: int, data: bytes) -> ResponseFrame:
        """Maintainer-only raw command path."""

        payload = build_command(cmd, data)
        return self._send_and_recv(payload, state_changing=True)

    def _send_payload(self, payload: bytes) -> ResponseFrame:
        """Maintainer-only prebuilt-payload path."""
        return self._send_and_recv(payload, state_changing=True)

    def read_words(self, addr: int, count: int) -> list[int]:
        """Read one or more basic-area words with `CMD=1C`."""
        resp = self._send_and_recv(build_word_read(addr, count), retryable=True)
        if resp.cmd != 0x1C:
            raise ToyopucProtocolError("Unexpected CMD in response")
        return unpack_u16_le(resp.data)

    def write_words(self, addr: int, values: Iterable[int]) -> None:
        """Write one or more basic-area words with `CMD=1D`."""
        resp = self._send_and_recv(build_word_write(addr, values), state_changing=True)
        if resp.cmd != 0x1D:
            raise ToyopucProtocolError("Unexpected CMD in response")

    def read_bytes(self, addr: int, count: int) -> bytes:
        """Read one or more basic-area bytes with `CMD=1E`."""
        resp = self._send_and_recv(build_byte_read(addr, count), retryable=True)
        if resp.cmd != 0x1E:
            raise ToyopucProtocolError("Unexpected CMD in response")
        return resp.data

    def write_bytes(self, addr: int, values: Iterable[int]) -> None:
        """Write one or more basic-area bytes with `CMD=1F`."""
        resp = self._send_and_recv(build_byte_write(addr, values), state_changing=True)
        if resp.cmd != 0x1F:
            raise ToyopucProtocolError("Unexpected CMD in response")

    def read_bit(self, addr: int) -> bool:
        """Read one basic-area bit with `CMD=20`."""
        resp = self._send_and_recv(build_bit_read(addr), retryable=True)
        if resp.cmd != 0x20:
            raise ToyopucProtocolError("Unexpected CMD in response")
        if len(resp.data) != 1:
            raise ToyopucProtocolError("Bit read response must be 1 byte")
        return resp.data[0] != 0

    def write_bit(self, addr: int, value: bool) -> None:
        """Write one basic-area bit with `CMD=21`."""
        resp = self._send_and_recv(build_bit_write(addr, _normalize_bit_value(value)), state_changing=True)
        if resp.cmd != 0x21:
            raise ToyopucProtocolError("Unexpected CMD in response")

    def read_dword(self, addr: int) -> int:
        """Read one 32-bit value from two consecutive words."""
        return self.read_dwords(addr, 1)[0]

    def write_dword(self, addr: int, value: int) -> None:
        """Write one 32-bit value to two consecutive words."""
        self.write_dwords(addr, [value])

    def read_dwords(self, addr: int, count: int) -> list[int]:
        """Read one or more 32-bit values from consecutive words."""
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError("count must be an integer >= 1")
        points = count
        return _unpack_uint32_low_word_first_words(self.read_words(addr, points * 2))

    def write_dwords(self, addr: int, values: Iterable[int]) -> None:
        """Write one or more 32-bit values to consecutive words."""
        self.write_words(addr, _pack_uint32_low_word_first_words(values))

    def read_float32(self, addr: int) -> float:
        """Read one IEEE-754 float32 from two consecutive words."""
        return self.read_float32s(addr, 1)[0]

    def write_float32(self, addr: int, value: float) -> None:
        """Write one IEEE-754 float32 to two consecutive words."""
        self.write_float32s(addr, [value])

    def read_float32s(self, addr: int, count: int) -> list[float]:
        """Read one or more IEEE-754 float32 values from consecutive words."""
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError("count must be an integer >= 1")
        points = count
        return _unpack_float32_low_word_first_words(self.read_words(addr, points * 2))

    def write_float32s(self, addr: int, values: Iterable[float]) -> None:
        """Write one or more IEEE-754 float32 values to consecutive words."""
        self.write_words(addr, _pack_float32_low_word_first_words(values))

    def read_words_multi(self, addrs: Iterable[int]) -> list[int]:
        """Read multiple non-contiguous basic-area words with `CMD=22`."""
        resp = self._send_and_recv(build_multi_word_read(addrs), retryable=True)
        if resp.cmd != 0x22:
            raise ToyopucProtocolError("Unexpected CMD in response")
        return unpack_u16_le(resp.data)

    def write_words_multi(self, pairs: Iterable[tuple[int, int]]) -> None:
        """Write multiple non-contiguous basic-area words with `CMD=23`."""
        resp = self._send_and_recv(build_multi_word_write(pairs), state_changing=True)
        if resp.cmd != 0x23:
            raise ToyopucProtocolError("Unexpected CMD in response")

    def read_bytes_multi(self, addrs: Iterable[int]) -> bytes:
        """Read multiple non-contiguous basic-area bytes with `CMD=24`."""
        resp = self._send_and_recv(build_multi_byte_read(addrs), retryable=True)
        if resp.cmd != 0x24:
            raise ToyopucProtocolError("Unexpected CMD in response")
        return resp.data

    def write_bytes_multi(self, pairs: Iterable[tuple[int, int]]) -> None:
        """Write multiple non-contiguous basic-area bytes with `CMD=25`."""
        resp = self._send_and_recv(build_multi_byte_write(pairs), state_changing=True)
        if resp.cmd != 0x25:
            raise ToyopucProtocolError("Unexpected CMD in response")

    def read_ext_words(self, no: int, addr: int, count: int) -> list[int]:
        """Read extended-area words with `CMD=94` using `(No., addr)`."""
        resp = self._send_and_recv(build_ext_word_read(no, addr, count), retryable=True)
        if resp.cmd != 0x94:
            raise ToyopucProtocolError("Unexpected CMD in response")
        return unpack_u16_le(resp.data)

    def write_ext_words(self, no: int, addr: int, values: Iterable[int]) -> None:
        """Write extended-area words with `CMD=95` using `(No., addr)`."""
        resp = self._send_and_recv(build_ext_word_write(no, addr, values), state_changing=True)
        if resp.cmd != 0x95:
            raise ToyopucProtocolError("Unexpected CMD in response")

    def read_ext_bytes(self, no: int, addr: int, count: int) -> bytes:
        """Read extended-area bytes with `CMD=96` using `(No., addr)`."""
        resp = self._send_and_recv(build_ext_byte_read(no, addr, count), retryable=True)
        if resp.cmd != 0x96:
            raise ToyopucProtocolError("Unexpected CMD in response")
        return resp.data

    def write_ext_bytes(self, no: int, addr: int, values: Iterable[int]) -> None:
        """Write extended-area bytes with `CMD=97` using `(No., addr)`."""
        resp = self._send_and_recv(build_ext_byte_write(no, addr, values), state_changing=True)
        if resp.cmd != 0x97:
            raise ToyopucProtocolError("Unexpected CMD in response")

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
        resp = self._send_and_recv(
            build_ext_multi_read(list(bit_points), list(byte_points), list(word_points)), retryable=True
        )
        if resp.cmd != 0x98:
            raise ToyopucProtocolError("Unexpected CMD in response")
        return resp.data

    def write_ext_multi(
        self,
        bit_points: Iterable[tuple[int, int, int, int]],
        byte_points: Iterable[tuple[int, int, int]],
        word_points: Iterable[tuple[int, int, int]],
    ) -> None:
        """Write mixed extended points with `CMD=99`.

        All `addr` fields are monitor byte addresses, including `word_points`
        (manual: "byte address N"), as in :meth:`read_ext_multi`.
        """
        resp = self._send_and_recv(
            build_ext_multi_write(list(bit_points), list(byte_points), list(word_points)), state_changing=True
        )
        if resp.cmd != 0x99:
            raise ToyopucProtocolError("Unexpected CMD in response")

    def pc10_block_read(self, addr32: int, count: int) -> bytes:
        """Read PC10 block data with `CMD=C2` from a 32-bit byte address."""
        resp = self._send_and_recv(build_pc10_block_read(addr32, count), retryable=True)
        if resp.cmd != 0xC2:
            raise ToyopucProtocolError("Unexpected CMD in response")
        if len(resp.data) != count:
            raise ToyopucProtocolError(
                f"PC10 block-read response size mismatch: expected={count}, actual={len(resp.data)}"
            )
        return resp.data

    def pc10_block_write(self, addr32: int, data_bytes: bytes) -> None:
        """Write PC10 block data with `CMD=C3` to a 32-bit byte address."""
        resp = self._send_and_recv(build_pc10_block_write(addr32, data_bytes), state_changing=True)
        if resp.cmd != 0xC3:
            raise ToyopucProtocolError("Unexpected CMD in response")

    def pc10_multi_read(self, payload: bytes) -> bytes:
        """Read PC10 multi-point data with `CMD=C4` using a prebuilt payload."""
        resp = self._send_and_recv(build_pc10_multi_read(payload), retryable=True)
        if resp.cmd != 0xC4:
            raise ToyopucProtocolError("Unexpected CMD in response")
        return resp.data

    def pc10_multi_write(self, payload: bytes) -> None:
        """Write PC10 multi-point data with `CMD=C5` using a prebuilt payload."""
        resp = self._send_and_recv(build_pc10_multi_write(payload), state_changing=True)
        if resp.cmd != 0xC5:
            raise ToyopucProtocolError("Unexpected CMD in response")

    def read_fr_words(self, index: int, count: int) -> list[int]:
        """Read FR words via exactly one PC10 block-read request (`CMD=C2`).

        `FR` real-hardware access uses 32-bit PC10 addressing with
        `Ex No.=0x40-0x7F`, not `CMD=94`.
        """
        start, word_count = _validate_fr_single_request(index, count)
        data = self.pc10_block_read(encode_fr_word_addr32(start), word_count * 2)
        return unpack_u16_le(data)

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
        resp = self._send_and_recv(build_fr_register(fr_block_ex_no(block_start)), state_changing=True)
        if resp.cmd != 0xCA:
            raise ToyopucProtocolError("Unexpected CMD in response")

    def relay_command(self, link_no: int, station_no: int, inner_payload: bytes) -> ResponseFrame:
        """Wrap a command in one relay hop using `CMD=60`."""
        read_only = _is_read_only_payload(inner_payload)
        return self._send_and_recv(
            build_relay_command(link_no, station_no, inner_payload),
            retryable=read_only,
            state_changing=not read_only,
        )

    def relay_nested(
        self,
        hops: Iterable[tuple[int, int]],
        inner_payload: bytes,
        *,
        retryable: bool | None = None,
        state_changing: bool | None = None,
    ) -> ResponseFrame:
        """Wrap a command in multiple relay hops using nested `CMD=60` frames."""
        read_only = _is_read_only_payload(inner_payload)
        return self._send_and_recv(
            build_relay_nested(list(hops), inner_payload),
            retryable=read_only if retryable is None else retryable,
            state_changing=not read_only if state_changing is None else state_changing,
        )

    def send_via_relay(self, hops: str | Iterable[tuple[int, int]], inner_payload: bytes) -> ResponseFrame:
        """Send a command through relay hops and return the final inner response."""
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
        outer = self.relay_nested(normalized, inner_payload)
        layers, final = unwrap_relay_response_chain(outer)
        if final is None:
            last = layers[-1]
            raise ToyopucProtocolError(
                f"Relay NAK at link=0x{last.link_no:02X}, station=0x{last.station_no:04X}, ack=0x{last.ack:02X}"
            )
        return final

    def relay_read_words(self, hops: str | Iterable[tuple[int, int]], addr: int, count: int) -> list[int]:
        """Read one or more basic-area words through relay hops."""
        resp = self.send_via_relay(hops, build_word_read(addr, count))
        if resp.cmd != 0x1C:
            raise ToyopucProtocolError("Unexpected CMD in relay word-read response")
        return unpack_u16_le(resp.data)

    def relay_write_words(self, hops: str | Iterable[tuple[int, int]], addr: int, values: Iterable[int]) -> None:
        """Write one or more basic-area words through relay hops."""
        resp = self.send_via_relay(hops, build_word_write(addr, values))
        if resp.cmd != 0x1D:
            raise ToyopucProtocolError("Unexpected CMD in relay word-write response")

    def relay_read_clock(self, hops: str | Iterable[tuple[int, int]]) -> ClockData:
        """Read the CPU clock through relay hops."""
        resp = self.send_via_relay(hops, build_clock_read())
        if resp.cmd != 0x32:
            raise ToyopucProtocolError("Unexpected CMD in relay clock response")
        try:
            return parse_clock_data(resp.data)
        except Exception as e:
            raise ToyopucProtocolError(f"Failed to parse relay clock response data={resp.data.hex()}") from e

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
        resp = self.send_via_relay(
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
        if resp.cmd != 0x32:
            raise ToyopucProtocolError("Unexpected CMD in relay clock-write response")
        if resp.data != bytes([0x71, 0x00]):
            raise ToyopucProtocolError("Unexpected relay clock-write response body")

    def relay_resume_scan(self, hops: str | Iterable[tuple[int, int]]) -> None:
        """Resume CPU scan through relay hops via `CMD=32 / 01 00`."""
        resp = self.send_via_relay(hops, build_scan_resume())
        if resp.cmd != 0x32:
            raise ToyopucProtocolError("Unexpected CMD in relay scan-resume response")
        if resp.data != bytes([0x01, 0x00]):
            raise ToyopucProtocolError("Unexpected relay scan-resume response body")

    def relay_stop_scan(self, hops: str | Iterable[tuple[int, int]]) -> None:
        """Stop CPU scan through relay hops via `CMD=32 / 02 00 01`."""
        resp = self.send_via_relay(hops, build_scan_stop())
        if resp.cmd != 0x32:
            raise ToyopucProtocolError("Unexpected CMD in relay scan-stop response")
        if resp.data != bytes([0x02, 0x00]):
            raise ToyopucProtocolError("Unexpected relay scan-stop response body")

    def relay_release_scan_stop(self, hops: str | Iterable[tuple[int, int]]) -> None:
        """Release CPU scan stop through relay hops via `CMD=32 / 02 00 00`."""
        resp = self.send_via_relay(hops, build_scan_stop_release())
        if resp.cmd != 0x32:
            raise ToyopucProtocolError("Unexpected CMD in relay scan-stop-release response")
        if resp.data != bytes([0x02, 0x00]):
            raise ToyopucProtocolError("Unexpected relay scan-stop-release response body")

    def relay_read_cpu_status(self, hops: str | Iterable[tuple[int, int]]) -> CpuStatusData:
        """Read the 8-byte CPU status block through relay hops."""
        resp = self.send_via_relay(hops, build_cpu_status_read())
        if resp.cmd != 0x32:
            raise ToyopucProtocolError("Unexpected CMD in relay CPU status response")
        try:
            return parse_cpu_status_data(resp.data)
        except Exception as e:
            raise ToyopucProtocolError(f"Failed to parse relay CPU status response data={resp.data.hex()}") from e

    def relay_read_cpu_status_a0_raw(self, hops: str | Iterable[tuple[int, int]]) -> bytes:
        """Read raw 8-byte CPU status through relay hops via `CMD=A0 / 00 11 00`."""
        resp = self.send_via_relay(hops, build_cpu_status_read_a0())
        if resp.cmd != 0xA0:
            raise ToyopucProtocolError("Unexpected CMD in relay A0 CPU status response")
        try:
            return parse_cpu_status_data_a0_raw(resp.data)
        except Exception as e:
            raise ToyopucProtocolError(f"Failed to parse relay A0 CPU status response data={resp.data.hex()}") from e

    def relay_read_cpu_status_a0(self, hops: str | Iterable[tuple[int, int]]) -> CpuStatusData:
        """Read decoded CPU status through relay hops via `CMD=A0 / 00 11 00`."""
        resp = self.send_via_relay(hops, build_cpu_status_read_a0())
        if resp.cmd != 0xA0:
            raise ToyopucProtocolError("Unexpected CMD in relay A0 CPU status response")
        try:
            return parse_cpu_status_data_a0(resp.data)
        except Exception as e:
            raise ToyopucProtocolError(f"Failed to parse relay A0 CPU status response data={resp.data.hex()}") from e

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
        resp = self.send_via_relay(hops, build_pc10_block_write(encode_fr_word_addr32(start), data))
        if resp.cmd != 0xC3:
            raise ToyopucProtocolError("Unexpected CMD in relay FR block-write response")

    def relay_commit_fr_block(
        self,
        hops: str | Iterable[tuple[int, int]],
        block_start_index: int,
    ) -> None:
        """Commit exactly one explicitly selected remote FR block."""
        block_start = _validate_fr_block_start(block_start_index)
        resp = self.send_via_relay(hops, build_fr_register(fr_block_ex_no(block_start)))
        if resp.cmd != 0xCA:
            raise ToyopucProtocolError("Unexpected CMD in relay FR-register response")

    def read_clock(self) -> ClockData:
        """Read the CPU clock via `CMD=32 / 70 00`."""
        resp = self._send_and_recv(build_clock_read(), retryable=True)
        if resp.cmd != 0x32:
            raise ToyopucProtocolError("Unexpected CMD in response")
        try:
            return parse_clock_data(resp.data)
        except Exception as e:
            raise ToyopucProtocolError(f"Failed to parse clock response data={resp.data.hex()}") from e

    def read_cpu_status(self) -> CpuStatusData:
        """Read the 8-byte CPU status block via `CMD=32 / 11 00`."""
        resp = self._send_and_recv(build_cpu_status_read())
        if resp.cmd != 0x32:
            raise ToyopucProtocolError("Unexpected CMD in response")
        try:
            return parse_cpu_status_data(resp.data)
        except Exception as e:
            raise ToyopucProtocolError(f"Failed to parse CPU status response data={resp.data.hex()}") from e

    def read_cpu_status_a0_raw(self) -> bytes:
        """Read raw 8-byte CPU status via `CMD=A0 / 00 11 00`.

        This command path is used in the flash/FR completion flow. The library
        currently returns the 8 raw status bytes because the exact bit mapping
        for this path has not been finalized yet.
        """
        resp = self._send_and_recv(build_cpu_status_read_a0())
        if resp.cmd != 0xA0:
            raise ToyopucProtocolError("Unexpected CMD in response")
        try:
            return parse_cpu_status_data_a0_raw(resp.data)
        except Exception as e:
            raise ToyopucProtocolError(f"Failed to parse A0 CPU status response data={resp.data.hex()}") from e

    def read_cpu_status_a0(self) -> CpuStatusData:
        """Read decoded CPU status via `CMD=A0 / 00 11 00`."""
        resp = self._send_and_recv(build_cpu_status_read_a0())
        if resp.cmd != 0xA0:
            raise ToyopucProtocolError("Unexpected CMD in response")
        try:
            return parse_cpu_status_data_a0(resp.data)
        except Exception as e:
            raise ToyopucProtocolError(f"Failed to parse A0 CPU status response data={resp.data.hex()}") from e

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
        resp = self._send_and_recv(
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
        if resp.cmd != 0x32:
            raise ToyopucProtocolError("Unexpected CMD in response")
        if resp.data != bytes([0x71, 0x00]):
            raise ToyopucProtocolError("Unexpected clock write response body")

    def resume_scan(self) -> None:
        """Resume CPU scan via `CMD=32 / 01 00`."""
        resp = self._send_and_recv(build_scan_resume(), state_changing=True)
        if resp.cmd != 0x32:
            raise ToyopucProtocolError("Unexpected CMD in response")
        if resp.data != bytes([0x01, 0x00]):
            raise ToyopucProtocolError("Unexpected scan-resume response body")

    def stop_scan(self) -> None:
        """Stop CPU scan via `CMD=32 / 02 00 01`."""
        resp = self._send_and_recv(build_scan_stop(), state_changing=True)
        if resp.cmd != 0x32:
            raise ToyopucProtocolError("Unexpected CMD in response")
        if resp.data != bytes([0x02, 0x00]):
            raise ToyopucProtocolError("Unexpected scan-stop response body")

    def release_scan_stop(self) -> None:
        """Release CPU scan stop via `CMD=32 / 02 00 00`."""
        resp = self._send_and_recv(build_scan_stop_release(), state_changing=True)
        if resp.cmd != 0x32:
            raise ToyopucProtocolError("Unexpected CMD in response")
        if resp.data != bytes([0x02, 0x00]):
            raise ToyopucProtocolError("Unexpected scan-stop-release response body")
