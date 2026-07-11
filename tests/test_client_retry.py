import socket
import time
from datetime import datetime, timezone
from threading import Event

import pytest

from toyopuc import ToyopucClient, ToyopucError, ToyopucProtocolError
from toyopuc.protocol import build_scan_resume, build_scan_stop, build_scan_stop_release


class _FakeSocket:
    def __init__(self, responses: list[bytes]) -> None:
        self._responses = list(responses)
        self._current = b""
        self._offset = 0
        self.sent: list[bytes] = []
        self.options: list[tuple[int, int, int]] = []

    def sendall(self, payload: bytes) -> None:
        self.sent.append(payload)
        self._current = self._responses.pop(0)
        self._offset = 0

    def recv_into(self, buffer, size: int = 0) -> int:
        requested = size or len(buffer)
        chunk = self._current[self._offset : self._offset + requested]
        buffer[: len(chunk)] = chunk
        self._offset += len(chunk)
        return len(chunk)

    def close(self) -> None:
        return None

    def setsockopt(self, level: int, optname: int, value: int) -> None:
        self.options.append((level, optname, value))


class _FakeUdpSocket:
    def __init__(self, response: bytes) -> None:
        self._response = response
        self.sent: list[tuple[bytes, tuple[str, int]]] = []
        self.recv_sizes: list[int] = []
        self.binds: list[tuple[str, int]] = []
        self.timeout: float | None = None

    def sendto(self, payload: bytes, address: tuple[str, int]) -> None:
        self.sent.append((payload, address))

    def recvfrom(self, size: int) -> tuple[bytes, tuple[str, int]]:
        self.recv_sizes.append(size)
        return self._response, ("127.0.0.1", 1025)

    def close(self) -> None:
        return None

    def bind(self, address: tuple[str, int]) -> None:
        self.binds.append(address)

    def settimeout(self, value: float) -> None:
        self.timeout = value


def _response(cmd: int, data: bytes = b"", *, rc: int = 0x00) -> bytes:
    length = 1 + len(data)
    return bytes([0x80, rc, length & 0xFF, (length >> 8) & 0xFF, cmd & 0xFF]) + data


def test_tcp_connect_enables_tcp_nodelay(monkeypatch: pytest.MonkeyPatch) -> None:
    sock = _FakeSocket([])

    def fake_create_connection(address: tuple[str, int], timeout: float) -> _FakeSocket:
        assert address == ("127.0.0.1", 1025)
        assert timeout == 3.0
        return sock

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")

    client.connect()

    assert sock.options == [(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)]


def test_connect_retries_pre_send_socket_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    sock = _FakeSocket([])
    calls = 0

    def fake_create_connection(address: tuple[str, int], timeout: float) -> _FakeSocket:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("temporary connect failure")
        return sock

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp", retries=1, retry_delay=0)

    client.connect()

    assert calls == 2
    assert client._sock is sock


def test_udp_send_and_recv_accepts_large_datagram_response() -> None:
    data = bytes(index & 0xFF for index in range(9000))
    sock = _FakeUdpSocket(_response(0x1C, data))
    client = ToyopucClient("127.0.0.1", 1025, transport="udp")
    client._sock = sock

    frame = client._send_raw(0x1C, b"")

    assert frame.cmd == 0x1C
    assert frame.data == data
    assert sock.recv_sizes == [65535]


def test_udp_connect_binds_ephemeral_local_port(monkeypatch: pytest.MonkeyPatch) -> None:
    sock = _FakeUdpSocket(_response(0x1C))
    monkeypatch.setattr(socket, "socket", lambda *args: sock)
    client = ToyopucClient("127.0.0.1", 1025, transport="udp")

    client.connect()

    assert sock.binds == [("", 0)]
    assert sock.timeout == 3.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"transport": ""},
        {"transport": "sctp"},
        {"transport": "tcp", "local_port": 1},
        {"transport": "udp", "local_port": -1},
        {"transport": "udp", "local_port": 65_536},
        {"transport": "tcp", "timeout": 0},
        {"transport": "tcp", "timeout": float("nan")},
        {"transport": "tcp", "retries": -1},
        {"transport": "tcp", "retries": True},
        {"transport": "tcp", "retry_delay": -1},
        {"transport": "tcp", "retry_delay": float("inf")},
    ],
)
def test_client_rejects_invalid_connection_values_before_socket(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        ToyopucClient("127.0.0.1", 1025, **kwargs)  # type: ignore[arg-type]


def test_maintainer_trace_exception_does_not_change_read_or_retry() -> None:
    sock = _FakeSocket([_response(0x1C, b"\x34\x12")])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp", retries=1)
    client._sock = sock
    traced: list[bytes] = []

    def broken_trace(frame) -> None:
        traced.append(frame.data)
        raise RuntimeError("diagnostic failure")

    client._maintainer_trace_hook = broken_trace

    assert client.read_words(0, 1) == [0x1234]
    assert client._trace_queue is not None
    client._trace_queue.join()
    assert traced == [sock.sent[0], _response(0x1C, b"\x34\x12")]
    assert len(sock.sent) == 1


def test_slow_maintainer_trace_does_not_delay_transport() -> None:
    sock = _FakeSocket([_response(0x1C, b"\x34\x12")])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    client._sock = sock
    release = Event()

    def slow_trace(frame) -> None:
        release.wait(1)

    client._maintainer_trace_hook = slow_trace
    started = time.monotonic()
    assert client.read_words(0, 1) == [0x1234]
    elapsed = time.monotonic() - started
    release.set()

    assert elapsed < 0.2


def test_send_and_recv_retries_response_error_0x73() -> None:
    sock = _FakeSocket(
        [
            _response(0x73, rc=0x10),
            _response(0x1C, b"\x34\x12"),
        ]
    )
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp", retries=1, retry_delay=0)
    client._sock = sock

    values = client.read_words(0, 1)

    assert values == [0x1234]
    assert len(sock.sent) == 2


def test_raw_command_never_retries_retryable_response() -> None:
    sock = _FakeSocket([_response(0x73, rc=0x10), _response(0x1C, b"\x34\x12")])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp", retries=1, retry_delay=0)
    client._sock = sock

    with pytest.raises(ToyopucError, match="error_code=0x73"):
        client._send_raw(0x1C, b"")

    assert len(sock.sent) == 1


def test_send_and_recv_exhausts_response_error_0x73_retries() -> None:
    sock = _FakeSocket([_response(0x73, rc=0x10)])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp", retries=0, retry_delay=0)
    client._sock = sock

    with pytest.raises(ToyopucError, match="error_code=0x73"):
        client._send_raw(0x1C, b"")

    assert len(sock.sent) == 1


def test_stop_scan_uses_scan_stop_frame() -> None:
    sock = _FakeSocket([_response(0x32, b"\x02\x00")])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp", retries=0, retry_delay=0)
    client._sock = sock

    client.stop_scan()

    assert sock.sent == [build_scan_stop()]


def test_resume_scan_uses_scan_resume_frame() -> None:
    sock = _FakeSocket([_response(0x32, b"\x01\x00")])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp", retries=0, retry_delay=0)
    client._sock = sock

    client.resume_scan()

    assert sock.sent == [build_scan_resume()]


def test_release_scan_stop_uses_scan_stop_release_frame() -> None:
    sock = _FakeSocket([_response(0x32, b"\x02\x00")])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp", retries=0, retry_delay=0)
    client._sock = sock

    client.release_scan_stop()

    assert sock.sent == [build_scan_stop_release()]


def test_stop_scan_rejects_unexpected_response_body() -> None:
    sock = _FakeSocket([_response(0x32, b"\x01\x00")])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp", retries=0, retry_delay=0)
    client._sock = sock

    with pytest.raises(ToyopucProtocolError, match="scan-stop response body"):
        client.stop_scan()


def test_clock_write_requires_explicit_matching_century_and_naive_value() -> None:
    sock = _FakeSocket([])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    client._sock = sock

    with pytest.raises(TypeError):
        client.write_clock(datetime(2026, 3, 15))  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="within"):
        client.write_clock(datetime(2026, 3, 15), year_base=1900)
    with pytest.raises(ValueError, match="timezone-naive"):
        client.write_clock(datetime(2026, 3, 15, tzinfo=timezone.utc), year_base=2000)
    assert sock.sent == []
