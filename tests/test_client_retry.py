import asyncio
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Event

import pytest

import toyopuc.client as client_module
from toyopuc import (
    AsyncToyopucClient,
    ToyopucClient,
    ToyopucClosedError,
    ToyopucError,
    ToyopucOperationOutcomeUnknownError,
    ToyopucOutcomeUnknownReason,
    ToyopucProtocolError,
    ToyopucTimeoutError,
    ToyopucTransportError,
)
from toyopuc.client import _is_read_only_payload
from toyopuc.protocol import ResponseFrame, build_command, build_scan_resume, build_scan_stop, build_scan_stop_release


class _FakeSocket:
    def __init__(self, responses: list[bytes]) -> None:
        self._responses = list(responses)
        self._current = b""
        self._offset = 0
        self.sent: list[bytes] = []
        self.options: list[tuple[int, int, int]] = []
        self.timeout: float | None = None

    def settimeout(self, value: float) -> None:
        self.timeout = value

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


class _FragmentedSocket(_FakeSocket):
    def recv_into(self, buffer, size: int = 0) -> int:
        return super().recv_into(buffer, min(size or len(buffer), 1))


class _FakeUdpSocket:
    def __init__(self, response: bytes) -> None:
        self._response = response
        self.sent: list[bytes] = []
        self.recv_sizes: list[int] = []
        self.binds: list[tuple[str, int]] = []
        self.timeout: float | None = None
        self.connected: tuple[str, int] | None = None

    def connect(self, address: tuple[str, int]) -> None:
        self.connected = address

    def send(self, payload: bytes) -> int:
        self.sent.append(payload)
        return len(payload)

    def recv(self, size: int) -> bytes:
        self.recv_sizes.append(size)
        return self._response

    def close(self) -> None:
        return None

    def bind(self, address: tuple[str, int]) -> None:
        self.binds.append(address)

    def settimeout(self, value: float) -> None:
        self.timeout = value


class _TimeoutAfterSendSocket(_FakeSocket):
    def __init__(self) -> None:
        super().__init__([])
        self.closed = False

    def sendall(self, payload: bytes) -> None:
        self.sent.append(payload)

    def recv_into(self, buffer, size: int = 0) -> int:
        raise TimeoutError("injected timeout")

    def close(self) -> None:
        self.closed = True


class _TimeoutUdpSocket(_FakeUdpSocket):
    def recv(self, size: int) -> bytes:
        self.recv_sizes.append(size)
        raise TimeoutError("injected timeout")


class _CloseTrackingSocket(_FakeSocket):
    def __init__(self) -> None:
        super().__init__([])
        self.closed = Event()

    def close(self) -> None:
        self.closed.set()


class _CloseTrackingUdpSocket(_FakeUdpSocket):
    def __init__(self) -> None:
        super().__init__(_response(0x1C))
        self.closed = Event()

    def close(self) -> None:
        self.closed.set()


class _ReconnectClient(ToyopucClient):
    def __init__(self, sockets: list[_FakeSocket], *, retries: int) -> None:
        super().__init__("127.0.0.1", 1025, transport="tcp", retries=retries, retry_delay=0)
        self._sockets = list(sockets)

    def _connect(self, deadline: float) -> None:
        self._sock = self._sockets.pop(0)


MAX_TIMER_SECONDS = 2_147_483.647


def _response(cmd: int, data: bytes = b"", *, rc: int = 0x00) -> bytes:
    length = 1 + len(data)
    return bytes([0x80, rc, length & 0xFF, (length >> 8) & 0xFF, cmd & 0xFF]) + data


def _relay_success_bytes(inner_cmd: int, inner_data: bytes) -> bytes:
    inner_raw = build_command(inner_cmd, inner_data)[2:]
    return bytes([0x80, 0x00]) + build_command(0x60, bytes([0x12, 0x02, 0x00, 0x06]) + inner_raw)[2:]


def test_tcp_fragmented_header_and_body_are_received_under_one_request() -> None:
    socket_ = _FragmentedSocket([_response(0x1C, bytes([0x34, 0x12]))])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    client._sock = socket_

    assert client.read_words(0, 1) == [0x1234]
    assert len(socket_.sent) == 1


def test_tcp_connect_enables_tcp_nodelay(monkeypatch: pytest.MonkeyPatch) -> None:
    sock = _FakeSocket([])

    def fake_create_connection(address: tuple[str, int], timeout: float) -> _FakeSocket:
        assert address == ("127.0.0.1", 1025)
        assert 0 < timeout <= 3.0
        return sock

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")

    client.connect()

    assert sock.options == [(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)]


def test_ipv4_literal_bypasses_resolver_for_tcp_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    sock = _FakeSocket([])
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args: pytest.fail("IPv4 literal must bypass DNS"))
    monkeypatch.setattr(socket, "create_connection", lambda *_args: sock)

    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    client.connect()

    assert client._sock is sock


@pytest.mark.parametrize("lazy", [False, True])
def test_delayed_dns_times_out_without_socket_or_late_adoption(
    monkeypatch: pytest.MonkeyPatch,
    lazy: bool,
) -> None:
    resolver_started = Event()
    release_resolver = Event()
    worker_finished = Event()
    socket_calls: list[tuple[str, int]] = []
    original_publish = client_module._publish_connection_attempt

    def delayed_getaddrinfo(host: str, port: int, family: int, socket_type: int):
        resolver_started.set()
        release_resolver.wait(1)
        return [(socket.AF_INET, socket_type, 0, "", ("192.0.2.10", port))]

    def fake_create_connection(endpoint: tuple[str, int], _timeout: float) -> _FakeSocket:
        socket_calls.append(endpoint)
        return _FakeSocket([])

    def publish_and_signal(*args: object) -> None:
        try:
            original_publish(*args)  # type: ignore[arg-type]
        finally:
            worker_finished.set()

    monkeypatch.setattr(socket, "getaddrinfo", delayed_getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    monkeypatch.setattr(client_module, "_publish_connection_attempt", publish_and_signal)
    client = ToyopucClient("plc.test", 1025, transport="tcp", timeout=0.02)

    try:
        with pytest.raises(ToyopucTimeoutError, match="Connect timeout"):
            if lazy:
                client.read_words(0, 1)
            else:
                client.connect()
        assert resolver_started.is_set()
        assert client._sock is None
        assert socket_calls == []
    finally:
        release_resolver.set()

    assert worker_finished.wait(1)
    assert client._sock is None
    assert socket_calls == []


@pytest.mark.parametrize("transport", ["tcp", "udp"])
def test_late_socket_completion_is_closed_and_never_adopted(
    monkeypatch: pytest.MonkeyPatch,
    transport: str,
) -> None:
    socket_phase_started = Event()
    release_socket_phase = Event()
    worker_finished = Event()
    original_publish = client_module._publish_connection_attempt

    def publish_and_signal(*args: object) -> None:
        try:
            original_publish(*args)  # type: ignore[arg-type]
        finally:
            worker_finished.set()

    monkeypatch.setattr(client_module, "_publish_connection_attempt", publish_and_signal)
    if transport == "tcp":
        late_socket: _CloseTrackingSocket | _CloseTrackingUdpSocket = _CloseTrackingSocket()

        def delayed_create_connection(_endpoint: tuple[str, int], _timeout: float) -> _CloseTrackingSocket:
            socket_phase_started.set()
            release_socket_phase.wait(1)
            return late_socket  # type: ignore[return-value]

        monkeypatch.setattr(socket, "create_connection", delayed_create_connection)
    else:
        late_socket = _CloseTrackingUdpSocket()
        original_bind = late_socket.bind

        def delayed_bind(address: tuple[str, int]) -> None:
            socket_phase_started.set()
            release_socket_phase.wait(1)
            original_bind(address)

        late_socket.bind = delayed_bind  # type: ignore[method-assign]
        monkeypatch.setattr(socket, "socket", lambda *_args: late_socket)

    client = ToyopucClient("127.0.0.1", 1025, transport=transport, timeout=0.02)
    try:
        with pytest.raises(ToyopucTimeoutError, match="Connect timeout"):
            client.connect()
        assert socket_phase_started.is_set()
        assert client._sock is None
    finally:
        release_socket_phase.set()

    assert worker_finished.wait(1)
    assert late_socket.closed.wait(1)
    assert client._sock is None


def test_native_connect_timeout_before_absolute_deadline_is_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def early_native_timeout(_endpoint: tuple[str, int], _timeout: float) -> _FakeSocket:
        raise TimeoutError("native candidate timeout")

    monkeypatch.setattr(socket, "create_connection", early_native_timeout)
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp", timeout=3)

    with pytest.raises(ToyopucTransportError) as caught:
        client.connect()
    assert isinstance(caught.value.__cause__, TimeoutError)
    assert client._sock is None


def test_pre_send_connect_retries_share_the_original_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    sock = _FakeSocket([])
    deadlines: list[float] = []

    def fake_attempt(
        _host: str,
        _port: int,
        _transport: str,
        _local_port: int,
        deadline: float,
        _cancellation_check: object,
    ) -> _FakeSocket:
        deadlines.append(deadline)
        if len(deadlines) == 1:
            raise OSError("first candidate failed")
        return sock

    monkeypatch.setattr(client_module, "_connection_attempt_before_deadline", fake_attempt)
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp", retries=1, retry_delay=0)
    client.connect()

    assert len(deadlines) == 2
    assert deadlines[0] == deadlines[1]
    assert client._sock is sock


@pytest.mark.parametrize("lazy", [False, True])
def test_async_connection_cancellation_does_not_wait_for_or_adopt_late_dns(
    monkeypatch: pytest.MonkeyPatch,
    lazy: bool,
) -> None:
    resolver_started = Event()
    release_resolver = Event()
    worker_finished = Event()
    original_publish = client_module._publish_connection_attempt

    def delayed_getaddrinfo(host: str, port: int, family: int, socket_type: int):
        resolver_started.set()
        release_resolver.wait(1)
        return [(socket.AF_INET, socket_type, 0, "", ("192.0.2.10", port))]

    def publish_and_signal(*args: object) -> None:
        try:
            original_publish(*args)  # type: ignore[arg-type]
        finally:
            worker_finished.set()

    monkeypatch.setattr(socket, "getaddrinfo", delayed_getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", lambda *_args: pytest.fail("late DNS must not connect"))
    monkeypatch.setattr(client_module, "_publish_connection_attempt", publish_and_signal)

    async def run() -> None:
        client = AsyncToyopucClient("plc.test", 1025, transport="tcp", timeout=3)
        task = asyncio.create_task(client.read_words(0, 1) if lazy else client.connect())
        try:
            assert await asyncio.to_thread(resolver_started.wait, 1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(task, 0.5)
            assert client._client._sock is None
            assert not worker_finished.is_set()
        finally:
            release_resolver.set()
        assert await asyncio.to_thread(worker_finished.wait, 1)
        assert client._client._sock is None
        await client.close()

    asyncio.run(run())


@pytest.mark.parametrize("lazy", [False, True])
def test_async_explicit_and_lazy_connect_share_the_bounded_dns_deadline(
    monkeypatch: pytest.MonkeyPatch,
    lazy: bool,
) -> None:
    resolver_started = Event()
    release_resolver = Event()
    worker_finished = Event()
    original_publish = client_module._publish_connection_attempt

    def delayed_getaddrinfo(host: str, port: int, family: int, socket_type: int):
        resolver_started.set()
        release_resolver.wait(1)
        return [(socket.AF_INET, socket_type, 0, "", ("192.0.2.10", port))]

    def publish_and_signal(*args: object) -> None:
        try:
            original_publish(*args)  # type: ignore[arg-type]
        finally:
            worker_finished.set()

    monkeypatch.setattr(socket, "getaddrinfo", delayed_getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", lambda *_args: pytest.fail("late DNS must not connect"))
    monkeypatch.setattr(client_module, "_publish_connection_attempt", publish_and_signal)

    async def run() -> None:
        client = AsyncToyopucClient("plc.test", 1025, transport="tcp", timeout=0.02)
        try:
            with pytest.raises(ToyopucTimeoutError, match="Connect timeout"):
                if lazy:
                    await client.read_words(0, 1)
                else:
                    await client.connect()
            assert resolver_started.is_set()
            assert client._client._sock is None
        finally:
            release_resolver.set()
        assert await asyncio.to_thread(worker_finished.wait, 1)
        assert client._client._sock is None
        await client.close()

    asyncio.run(run())


def test_close_during_dns_is_distinct_and_cannot_adopt_late_result(monkeypatch: pytest.MonkeyPatch) -> None:
    resolver_started = Event()
    release_resolver = Event()
    worker_finished = Event()
    original_publish = client_module._publish_connection_attempt

    def delayed_getaddrinfo(host: str, port: int, family: int, socket_type: int):
        resolver_started.set()
        release_resolver.wait(1)
        return [(socket.AF_INET, socket_type, 0, "", ("192.0.2.10", port))]

    def publish_and_signal(*args: object) -> None:
        try:
            original_publish(*args)  # type: ignore[arg-type]
        finally:
            worker_finished.set()

    monkeypatch.setattr(socket, "getaddrinfo", delayed_getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", lambda *_args: pytest.fail("closed DNS must not connect"))
    monkeypatch.setattr(client_module, "_publish_connection_attempt", publish_and_signal)
    client = ToyopucClient("plc.test", 1025, transport="tcp", timeout=3)

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            connecting = executor.submit(client.connect)
            assert resolver_started.wait(1)
            client.close()
            with pytest.raises(ToyopucClosedError, match="retired by close"):
                connecting.result(timeout=0.5)
        assert client._sock is None
        assert not worker_finished.is_set()
    finally:
        release_resolver.set()

    assert worker_finished.wait(1)
    assert client._sock is None


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

    assert client.traffic_stats().request_count == 0
    frame = client._send_raw(0x1C, b"")

    assert frame.cmd == 0x1C
    assert frame.data == data
    assert sock.recv_sizes == [65535]
    assert client.traffic_stats().request_count == 1
    assert client.traffic_stats().tx_bytes == len(sock.sent[0])
    assert client.traffic_stats().rx_bytes == len(_response(0x1C, data))
    client.close()
    assert client.traffic_stats().request_count == 1


def test_udp_connect_binds_ephemeral_local_port(monkeypatch: pytest.MonkeyPatch) -> None:
    sock = _FakeUdpSocket(_response(0x1C))
    socket_args: list[tuple[int, int]] = []

    def fake_socket(family: int, socket_type: int) -> _FakeUdpSocket:
        socket_args.append((family, socket_type))
        return sock

    monkeypatch.setattr(socket, "socket", fake_socket)
    client = ToyopucClient("127.0.0.1", 1025, transport="udp")

    client.connect()

    assert sock.binds == [("", 0)]
    assert sock.connected == ("127.0.0.1", 1025)
    assert sock.timeout is not None
    assert 0 < sock.timeout <= 3.0
    assert socket_args == [(socket.AF_INET, socket.SOCK_DGRAM)]


@pytest.mark.parametrize("transport", ["tcp", "udp"])
@pytest.mark.parametrize("host", ["::1", "[::1]", "::ffff:127.0.0.1"])
def test_client_rejects_ipv6_literals_before_resolution_or_socket(
    monkeypatch: pytest.MonkeyPatch,
    transport: str,
    host: str,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: pytest.fail("must not resolve"))
    monkeypatch.setattr(socket, "socket", lambda *_args, **_kwargs: pytest.fail("must not create socket"))

    with pytest.raises(ValueError, match="must be an IPv4 address"):
        ToyopucClient(host, 1025, transport=transport)
    with pytest.raises(ValueError, match="must be an IPv4 address"):
        AsyncToyopucClient(host, 1025, transport=transport)


def test_hostname_resolution_selects_first_ipv4_for_tcp_and_udp(monkeypatch: pytest.MonkeyPatch) -> None:
    resolution_calls: list[tuple[str, int, int, int]] = []

    def fake_getaddrinfo(host: str, port: int, family: int, socket_type: int):
        resolution_calls.append((host, port, family, socket_type))
        return [
            (socket.AF_INET6, socket_type, 0, "", ("::1", port, 0, 0)),
            (socket.AF_INET, socket_type, 0, "", ("192.0.2.10", port)),
            (socket.AF_INET, socket_type, 0, "", ("192.0.2.11", port)),
        ]

    tcp_socket = _FakeSocket([])
    tcp_endpoints: list[tuple[str, int]] = []

    def fake_create_connection(endpoint: tuple[str, int], timeout: float) -> _FakeSocket:
        assert 0 < timeout <= 3.0
        tcp_endpoints.append(endpoint)
        return tcp_socket

    udp_socket = _FakeUdpSocket(_response(0x1C))
    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    monkeypatch.setattr(socket, "socket", lambda family, socket_type: udp_socket)

    tcp_client = ToyopucClient("plc.local", 1025, transport="tcp")
    tcp_client.connect()
    udp_client = ToyopucClient("plc.local", 1025, transport="udp")
    udp_client.connect()

    assert tcp_endpoints == [("192.0.2.10", 1025)]
    assert udp_socket.connected == ("192.0.2.10", 1025)
    assert resolution_calls == [
        ("plc.local", 1025, socket.AF_INET, socket.SOCK_STREAM),
        ("plc.local", 1025, socket.AF_INET, socket.SOCK_DGRAM),
    ]


@pytest.mark.parametrize("transport", ["tcp", "udp"])
def test_hostname_without_ipv4_fails_before_socket_creation(
    monkeypatch: pytest.MonkeyPatch,
    transport: str,
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args: (_ for _ in ()).throw(socket.gaierror("no IPv4")))
    monkeypatch.setattr(socket, "create_connection", lambda *_args: pytest.fail("must not connect"))
    monkeypatch.setattr(socket, "socket", lambda *_args: pytest.fail("must not create socket"))
    client = ToyopucClient("ipv6-only.invalid", 1025, transport=transport)

    with pytest.raises(ToyopucError, match="Socket connection failed"):
        client.connect()

    assert client._sock is None


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


@pytest.mark.parametrize(
    "kwargs",
    [
        {"transport": "tcp", "timeout": MAX_TIMER_SECONDS + 0.001},
        {"transport": "tcp", "retry_delay": MAX_TIMER_SECONDS + 0.001},
        {"transport": "tcp", "timeout": 10**10_000},
        {"transport": "tcp", "retry_delay": 10**10_000},
    ],
)
def test_client_rejects_timer_overflow_values_as_value_error(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="no greater than 2147483.647 seconds"):
        ToyopucClient("127.0.0.1", 1025, **kwargs)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="no greater than 2147483.647 seconds"):
        AsyncToyopucClient("127.0.0.1", 1025, **kwargs)  # type: ignore[arg-type]


def test_client_accepts_the_common_timer_boundary() -> None:
    client = ToyopucClient(
        "127.0.0.1",
        1025,
        transport="tcp",
        timeout=MAX_TIMER_SECONDS,
        retry_delay=MAX_TIMER_SECONDS,
    )

    assert client.timeout == MAX_TIMER_SECONDS
    assert client.retry_delay == MAX_TIMER_SECONDS


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


def test_read_does_not_retry_plc_response_after_possible_send() -> None:
    sock = _FakeSocket(
        [
            _response(0x73, rc=0x10),
            _response(0x1C, b"\x34\x12"),
        ]
    )
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp", retries=1, retry_delay=0)
    client._sock = sock

    with pytest.raises(ToyopucError, match="error_code=0x73"):
        client.read_words(0, 1)

    assert len(sock.sent) == 1
    assert client.traffic_stats().request_count == 1


def test_cpu_status_read_methods_are_classified_read_only() -> None:
    class CaptureClient(ToyopucClient):
        def __init__(self) -> None:
            super().__init__("127.0.0.1", 1025, transport="tcp")
            self.state_changing_values: list[bool] = []

        def _send_and_recv(
            self,
            payload: bytes,
            *,
            state_changing: bool = False,
        ) -> ResponseFrame:
            self.state_changing_values.append(state_changing)
            cmd = payload[4]
            data = b"\x11\x00" + bytes(8) if cmd == 0x32 else b"\x00\x11\x00" + bytes(8)
            return ResponseFrame(ft=0x80, rc=0, cmd=cmd, data=data)

    client = CaptureClient()
    client.read_cpu_status()
    client.read_cpu_status_a0_raw()
    client.read_cpu_status_a0()

    assert client.state_changing_values == [False, False, False]


def test_read_only_classifier_accepts_full_and_trimmed_frames_structurally() -> None:
    full = build_command(0x1C, b"\x00\x00\x01\x00")
    trimmed = full[2:]

    assert _is_read_only_payload(full)
    assert _is_read_only_payload(trimmed)
    assert not _is_read_only_payload(build_command(0x1D, b"\x00\x00\x01\x00"))
    assert not _is_read_only_payload(build_command(0x1D, b"\x00\x00\x01\x00")[2:])


def test_read_only_classifier_does_not_confuse_trimmed_length_low_byte_zero_with_full_frame() -> None:
    trimmed = bytes([0x00, 0x01, 0x1C]) + bytes(255)

    assert len(trimmed) == 258
    assert _is_read_only_payload(trimmed)


@pytest.mark.parametrize("data", [b"\x34", b"\x34\x12\x56\x78"])
def test_fixed_size_word_read_rejects_short_and_long_responses(data: bytes) -> None:
    sock = _FakeSocket([_response(0x1C, data)])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    client._sock = sock

    with pytest.raises(ToyopucProtocolError, match="response data size mismatch"):
        client.read_words(0, 1)


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


def test_relay_read_and_write_do_not_retry_after_possible_send() -> None:
    read_sock = _FakeSocket([_response(0x73, rc=0x10), _relay_success_bytes(0x1C, b"\x34\x12")])
    read_client = ToyopucClient("127.0.0.1", 1025, transport="tcp", retries=1, retry_delay=0)
    read_client._sock = read_sock

    with pytest.raises(ToyopucError, match="error_code=0x73"):
        read_client.relay_read_words("P1-L2:N2", 0, 1)
    assert len(read_sock.sent) == 1

    write_sock = _FakeSocket([_response(0x73, rc=0x10), _relay_success_bytes(0x1D, b"")])
    write_client = ToyopucClient("127.0.0.1", 1025, transport="tcp", retries=1, retry_delay=0)
    write_client._sock = write_sock

    with pytest.raises(ToyopucError, match="error_code=0x73"):
        write_client.relay_write_words("P1-L2:N2", 0, [1])
    assert len(write_sock.sent) == 1


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

    with pytest.raises(ToyopucOperationOutcomeUnknownError):
        client.stop_scan()


def test_direct_and_relay_write_response_bodies_are_exact_and_unknown_when_malformed() -> None:
    direct_socket = _FakeSocket([_response(0x1D, b"\x00")])
    direct = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    direct._sock = direct_socket

    with pytest.raises(ToyopucOperationOutcomeUnknownError) as direct_error:
        direct.write_words(0, [1])
    assert direct_error.value.reason is ToyopucOutcomeUnknownReason.MALFORMED_RESPONSE

    relay_socket = _FakeSocket([_relay_success_bytes(0x1D, b"\x00")])
    relay = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    relay._sock = relay_socket

    with pytest.raises(ToyopucOperationOutcomeUnknownError) as relay_error:
        relay.relay_write_words("P1-L2:N2", 0, [1])
    assert relay_error.value.reason is ToyopucOutcomeUnknownReason.MALFORMED_RESPONSE


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


def test_state_changing_timeout_reports_unknown_outcome() -> None:
    sock = _TimeoutAfterSendSocket()
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    client._sock = sock

    with pytest.raises(ToyopucOperationOutcomeUnknownError) as captured:
        client.write_words(0, [1])

    assert captured.value.reason is ToyopucOutcomeUnknownReason.TIMEOUT
    assert isinstance(captured.value.cause, TimeoutError)
    assert captured.value.__cause__ is captured.value.cause
    assert len(sock.sent) == 1
    assert client.traffic_stats().request_count == 1
    assert client.traffic_stats().tx_bytes == len(sock.sent[0])
    assert client.traffic_stats().rx_bytes == 0


@pytest.mark.parametrize("value", [0, 1, 2, "1", None])
def test_low_level_bit_write_rejects_every_non_bool_before_transport(value: object) -> None:
    sock = _FakeSocket([])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    client._sock = sock

    with pytest.raises(ValueError, match="must be bool"):
        client.write_bit(0, value)  # type: ignore[arg-type]

    assert sock.sent == []
    assert client.traffic_stats().request_count == 0


@pytest.mark.parametrize("value", [False, True])
def test_low_level_bit_writes_accept_boolean_values(value: bool) -> None:
    bit_socket = _FakeSocket([_response(0x21)])
    bit_client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    bit_client._sock = bit_socket
    bit_client.write_bit(0, value)

    ext_socket = _FakeSocket([_response(0x99)])
    ext_client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    ext_client._sock = ext_socket
    ext_client.write_ext_multi([(1, 0, 0, value)], [], [])

    assert bit_socket.sent[0][-1] == int(value)
    assert ext_socket.sent[0][-1] == int(value)


@pytest.mark.parametrize("value", [0, 1])
def test_low_level_extended_bit_write_rejects_integer_bits_before_transport(value: int) -> None:
    sock = _FakeSocket([])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    client._sock = sock

    with pytest.raises(ValueError, match="must be bool"):
        client.write_ext_multi([(1, 0, 0, value)], [], [])  # type: ignore[list-item]

    assert sock.sent == []
    assert client.traffic_stats().request_count == 0


def test_fixed_port_udp_session_is_terminal_after_uncertain_timeout() -> None:
    sock = _TimeoutUdpSocket(_response(0x1C))
    client = ToyopucClient("127.0.0.1", 1025, transport="udp", local_port=20000)
    client._sock = sock

    with pytest.raises(ToyopucTimeoutError):
        client.read_words(0, 1)
    with pytest.raises(ToyopucError, match="cannot be reused"):
        client.connect()


def test_fixed_port_udp_session_is_terminal_after_malformed_write_response() -> None:
    sock = _FakeUdpSocket(b"\x80")
    client = ToyopucClient("127.0.0.1", 1025, transport="udp", local_port=20000)
    client._sock = sock

    with pytest.raises(ToyopucOperationOutcomeUnknownError):
        client.write_words(0, [1])
    with pytest.raises(ToyopucError, match="cannot be reused"):
        client.connect()


def test_graceful_eof_never_retries_and_write_outcome_is_unknown() -> None:
    read_client = _ReconnectClient(
        [_FakeSocket([b""]), _FakeSocket([_response(0x1C, b"\x34\x12")])],
        retries=1,
    )
    with pytest.raises(ToyopucError, match="Socket error"):
        read_client.read_words(0, 1)
    assert len(read_client._sockets) == 1

    write_client = _ReconnectClient([_FakeSocket([b""])], retries=1)
    with pytest.raises(ToyopucOperationOutcomeUnknownError):
        write_client.write_words(0, [1])


def test_timed_out_tcp_transport_can_explicitly_reconnect_and_exchange_on_same_client() -> None:
    timed_out = _TimeoutAfterSendSocket()
    recovered = _FakeSocket([_response(0x1C, b"\x34\x12")])
    client = _ReconnectClient([timed_out, recovered], retries=0)

    with pytest.raises(ToyopucTimeoutError):
        client.read_words(0, 1)
    assert timed_out.closed
    assert client._sock is None

    client.connect()
    assert client.read_words(0, 1) == [0x1234]
    assert client._sock is recovered


def test_canceling_queued_async_call_does_not_cancel_running_call() -> None:
    started = Event()
    release = Event()

    class SyncClient:
        def __init__(self) -> None:
            self.cancel_calls = 0
            self.clear_calls = 0
            self.executed: list[str] = []

        def first(self) -> str:
            started.set()
            release.wait(2)
            self.executed.append("first")
            return "first"

        def later(self, name: str) -> str:
            self.executed.append(name)
            return name

        def _begin_operation_cancel_scope(self, cancel_event: Event) -> None:
            self.cancel_event = cancel_event

        def _end_operation_cancel_scope(self, cancel_event: Event) -> None:
            assert self.cancel_event is cancel_event
            self.clear_calls += 1

        def _cancel_pending_operation(self, cancel_event: Event) -> None:
            assert self.cancel_event is cancel_event
            self.cancel_calls += 1

    async def run() -> None:
        wrapper = AsyncToyopucClient.__new__(AsyncToyopucClient)
        sync_client = SyncClient()
        executor = ThreadPoolExecutor(max_workers=1)
        object.__setattr__(wrapper, "_client", sync_client)
        object.__setattr__(wrapper, "_executor", executor)
        try:
            first = asyncio.create_task(wrapper._run_sync_in_worker(sync_client.first))
            assert await asyncio.to_thread(started.wait, 1)
            queued = asyncio.create_task(wrapper._run_sync_in_worker(sync_client.later, "queued"))
            await asyncio.sleep(0)
            queued.cancel()
            with pytest.raises(asyncio.CancelledError):
                await queued
            assert sync_client.cancel_calls == 0
            release.set()
            assert await first == "first"
            assert await wrapper._run_sync_in_worker(sync_client.later, "last") == "last"
            assert sync_client.executed == ["first", "last"]
        finally:
            release.set()
            executor.shutdown(wait=True, cancel_futures=True)

    asyncio.run(run())


def test_canceling_running_async_call_does_not_cancel_the_next_generation() -> None:
    started = Event()

    async def run() -> None:
        sync_client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
        wrapper = AsyncToyopucClient.__new__(AsyncToyopucClient)
        executor = ThreadPoolExecutor(max_workers=1)
        object.__setattr__(wrapper, "_client", sync_client)
        object.__setattr__(wrapper, "_executor", executor)

        def first() -> None:
            started.set()
            while True:
                sync_client._raise_if_cancelled()
                time.sleep(0.001)

        try:
            running = asyncio.create_task(wrapper._run_sync_in_worker(first))
            assert await asyncio.to_thread(started.wait, 1)
            running.cancel()
            with pytest.raises(asyncio.CancelledError):
                await running
            assert await wrapper._run_sync_in_worker(lambda: "next") == "next"
        finally:
            executor.shutdown(wait=True, cancel_futures=True)

    asyncio.run(run())


def test_lazy_connect_send_receive_and_decode_share_one_monotonic_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticks = iter(100.0 + index / 10 for index in range(20))
    monkeypatch.setattr(time, "monotonic", lambda: next(ticks))
    sock = _FakeSocket([_response(0x1C, b"\x34\x12")])
    connect_timeouts: list[float] = []
    socket_timeouts: list[float] = []
    original_settimeout = sock.settimeout

    def record_timeout(value: float) -> None:
        socket_timeouts.append(value)
        original_settimeout(value)

    sock.settimeout = record_timeout  # type: ignore[method-assign]

    def fake_connection_attempt(
        _host: str,
        _port: int,
        _transport: str,
        _local_port: int,
        deadline: float,
        _cancellation_check: object,
    ) -> _FakeSocket:
        connect_timeouts.append(client_module._remaining_time(deadline, "Connect timeout"))
        return sock

    monkeypatch.setattr(client_module, "_connection_attempt_before_deadline", fake_connection_attempt)
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp", timeout=3)

    assert client.read_words(0, 1) == [0x1234]
    assert connect_timeouts == [pytest.approx(2.9)]
    assert socket_timeouts == pytest.approx([2.7, 2.6, 2.5])


def test_state_change_is_not_unknown_when_transport_fails_before_send_attempt() -> None:
    class SetTimeoutFailureSocket(_FakeSocket):
        def settimeout(self, value: float) -> None:
            raise OSError("cannot configure timeout")

    sock = SetTimeoutFailureSocket([])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    client._sock = sock

    with pytest.raises(ToyopucTransportError):
        client.write_words(0, [1])
    assert sock.sent == []


@pytest.mark.parametrize(
    "operation",
    [
        lambda client: client.read_words(0, 0x0201),
        lambda client: client.write_words(0, [0] * 0x0201),
        lambda client: client.read_bytes(0, 0x0401),
        lambda client: client.write_bytes(0, bytes(0x0401)),
        lambda client: client.read_words_multi(range(0x0081)),
        lambda client: client.write_words_multi([(index, 0) for index in range(0x0081)]),
        lambda client: client.read_bytes_multi(range(0x0081)),
        lambda client: client.write_bytes_multi([(index, 0) for index in range(0x0081)]),
        lambda client: client.read_ext_words(0, 0, 0x0201),
        lambda client: client.write_ext_words(0, 0, [0] * 0x0201),
        lambda client: client.read_ext_bytes(0, 0, 0x0401),
        lambda client: client.write_ext_bytes(0, 0, bytes(0x0401)),
        lambda client: client.read_ext_multi([(0, 0, index) for index in range(0x00B1)], [], []),
        lambda client: client.write_ext_multi([(0, 0, index, False) for index in range(0x0081)], [], []),
        lambda client: client.pc10_block_read(0, 0x03F1),
        lambda client: client.pc10_block_write(0, bytes(0x03F1)),
        lambda client: client.pc10_multi_read(bytes(0x0201)),
        lambda client: client.pc10_multi_write(bytes(0x0201)),
    ],
)
def test_every_over_capacity_client_call_fails_without_transport_or_diagnostic_state(operation) -> None:
    sock = _FakeSocket([])
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    client._sock = sock

    with pytest.raises(ValueError):
        operation(client)

    assert sock.sent == []
    assert client.last_tx is None
    assert client.last_rx is None
    assert client.traffic_stats().request_count == 0


def test_sync_operation_gate_is_fifo_and_independent_per_client() -> None:
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    other = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    first_entered = Event()
    second_attempted = Event()
    release = Event()
    order: list[str] = []

    def run(name: str) -> None:
        if name == "second":
            second_attempted.set()
        with client._operation_turn():
            order.append(name)
            if name == "first":
                first_entered.set()
                release.wait(1)

    with ThreadPoolExecutor(max_workers=3) as executor:
        first = executor.submit(run, "first")
        assert first_entered.wait(1)
        second = executor.submit(run, "second")
        assert second_attempted.wait(1)
        third = executor.submit(run, "third")
        with other._operation_turn():
            assert order == ["first"]
        release.set()
        first.result(timeout=1)
        second.result(timeout=1)
        third.result(timeout=1)

    assert order == ["first", "second", "third"]


def test_close_retires_active_and_queued_generation_but_allows_new_work() -> None:
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    active = Event()
    queued = Event()
    release = Event()

    def first() -> None:
        with client._operation_turn():
            active.set()
            release.wait(1)
            client._raise_if_cancelled()

    def second() -> None:
        queued.set()
        with client._operation_turn():
            raise AssertionError("retired queued work must not execute")

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(first)
        assert active.wait(1)
        second_future = executor.submit(second)
        assert queued.wait(1)
        client.close()
        release.set()
        with pytest.raises(ToyopucClosedError):
            first_future.result(timeout=1)
        with pytest.raises(ToyopucClosedError):
            second_future.result(timeout=1)

    with client._operation_turn():
        pass


def test_async_close_retires_admitted_generation_and_new_call_uses_next_generation() -> None:
    client = AsyncToyopucClient("127.0.0.1", 1025, transport="tcp")
    active = Event()
    release = Event()

    def first(sync_client: ToyopucClient) -> str:
        active.set()
        release.wait(1)
        sync_client._raise_if_cancelled()
        return "first"

    async def run() -> None:
        first_task = asyncio.create_task(client._run_exclusive(first))
        assert await asyncio.to_thread(active.wait, 1)
        queued_task = asyncio.create_task(client._run_exclusive(lambda _client: "queued"))
        await asyncio.sleep(0)
        await client.close()
        release.set()
        with pytest.raises(ToyopucClosedError):
            await first_task
        with pytest.raises(ToyopucClosedError):
            await queued_task
        assert await client._run_exclusive(lambda _client: "new") == "new"

    asyncio.run(run())


def test_async_public_call_snapshots_mutable_input_before_waiting_in_fifo() -> None:
    started = Event()
    release = Event()

    class SyncClient:
        def __init__(self) -> None:
            self.values: list[int] | None = None
            self.cancel_event: Event | None = None

        def first(self) -> None:
            started.set()
            release.wait(1)

        def write_words(self, address: int, values: list[int] | tuple[int, ...]) -> None:
            assert address == 0
            self.values = list(values)

        def _begin_operation_cancel_scope(self, cancel_event: Event) -> None:
            self.cancel_event = cancel_event

        def _end_operation_cancel_scope(self, cancel_event: Event) -> None:
            assert self.cancel_event is cancel_event
            self.cancel_event = None

        def _cancel_pending_operation(self, cancel_event: Event) -> None:
            cancel_event.set()

    async def run() -> None:
        wrapper = AsyncToyopucClient.__new__(AsyncToyopucClient)
        sync_client = SyncClient()
        executor = ThreadPoolExecutor(max_workers=1)
        object.__setattr__(wrapper, "_client", sync_client)
        object.__setattr__(wrapper, "_executor", executor)
        try:
            first_task = asyncio.create_task(wrapper._run_sync_in_worker(sync_client.first))
            assert await asyncio.to_thread(started.wait, 1)
            values = [1, 2]
            write_task = asyncio.create_task(wrapper.write_words(0, values))
            await asyncio.sleep(0)
            values[0] = 9
            values.append(3)
            release.set()
            await first_task
            await write_task
            assert sync_client.values == [1, 2]
        finally:
            release.set()
            executor.shutdown(wait=True, cancel_futures=True)

    asyncio.run(run())
