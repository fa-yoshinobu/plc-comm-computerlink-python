from __future__ import annotations

import asyncio
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any, TypeVar, cast

from .client import ToyopucClient, ToyopucTraceDirection, _invoke_prepared_operation, _prepare_bound_operation_plan
from .errors import (
    ToyopucClosedError,
    ToyopucNotConnectedError,
    ToyopucOperationOutcomeUnknownError,
    ToyopucOutcomeUnknownReason,
    ToyopucProtocolError,
    ToyopucTimeoutError,
    ToyopucTransportError,
)
from .high_level import ToyopucDeviceClient, _require_positive_count

_T = TypeVar("_T")
_UDP_RECEIVE_BUFFER_SIZE = 65_535


class _AsyncIoRequired(Exception):
    def __init__(self, payload: bytes, state_changing: bool) -> None:
        super().__init__("native async transport exchange required")
        self.payload = payload
        self.state_changing = state_changing


@dataclass(frozen=True)
class _CompletedExchange:
    payload: bytes
    state_changing: bool
    frame: bytes


class _OperationScript:
    """Replays completed exchanges while the shared pure command core advances."""

    def __init__(self) -> None:
        self.completed: list[_CompletedExchange] = []
        self.cursor = 0

    def reset(self) -> None:
        self.cursor = 0

    def exchange(self, payload: bytes, state_changing: bool) -> bytes:
        if self.cursor == len(self.completed):
            raise _AsyncIoRequired(payload, state_changing)
        completed = self.completed[self.cursor]
        if completed.payload != payload or completed.state_changing != state_changing:
            raise ToyopucProtocolError("Prepared async operation changed its request sequence during replay")
        self.cursor += 1
        return completed.frame


def _install_async_wrapper(async_cls: type, method_name: str) -> None:
    async def _async_method(self: Any, *args: Any, **kwargs: Any) -> Any:
        bound = getattr(self._client, method_name)
        plan = _prepare_bound_operation_plan(bound, args, kwargs)
        return await self._run_native_callable(_invoke_prepared_operation, bound, plan)

    _async_method.__name__ = method_name
    _async_method.__qualname__ = f"{async_cls.__name__}.{method_name}"
    setattr(async_cls, method_name, _async_method)


class _AsyncToyopucClientBase:
    _sync_client_cls: type[Any] = ToyopucClient

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        object.__setattr__(self, "_client", self._sync_client_cls(*args, **kwargs))
        object.__setattr__(self, "_operation_lock", asyncio.Lock())
        object.__setattr__(self, "_socket", None)
        object.__setattr__(self, "_generation", 0)
        object.__setattr__(self, "_explicit_reconnect_required", False)

    def _ensure_runtime(self) -> None:
        # Private test adapters historically replaced only `_client`; lazy
        # initialization keeps those pure adapters usable without sync transport state.
        if "_operation_lock" not in self.__dict__:
            object.__setattr__(self, "_operation_lock", asyncio.Lock())
        if "_socket" not in self.__dict__:
            object.__setattr__(self, "_socket", None)
        if "_generation" not in self.__dict__:
            object.__setattr__(self, "_generation", 0)
        if "_explicit_reconnect_required" not in self.__dict__:
            object.__setattr__(self, "_explicit_reconnect_required", False)

    async def connect(self) -> None:
        self._ensure_runtime()
        async with self._operation_lock:
            deadline = asyncio.get_running_loop().time() + float(self._client.timeout)
            object.__setattr__(self, "_explicit_reconnect_required", False)
            if self._socket is None:
                await self._open_socket(deadline, self._generation)

    async def close(self) -> None:
        """Interrupt active work, retire its generation, and permit explicit reconnect."""

        self._ensure_runtime()
        object.__setattr__(self, "_generation", self._generation + 1)
        object.__setattr__(self, "_explicit_reconnect_required", True)
        self._close_socket()
        self._client.close()

    async def _run_exclusive(self, operation: Callable[[Any], _T]) -> _T:
        def invoke() -> _T:
            with self._client._operation_turn():
                return operation(self._client)

        return cast(_T, await self._run_native_callable(invoke))

    async def _run_native_callable(self, func: Callable[..., _T], /, *args: Any, **kwargs: Any) -> _T:
        self._ensure_runtime()
        async with self._operation_lock:
            loop = asyncio.get_running_loop()
            deadline = loop.time() + float(self._client.timeout)
            generation = self._generation
            script = _OperationScript()
            while True:
                script.reset()
                pending: _AsyncIoRequired | None = None
                self._client._async_transport_script = script
                try:
                    result = func(*args, **kwargs)
                except _AsyncIoRequired as required:
                    pending = required
                except asyncio.CancelledError:
                    raise
                except ToyopucOperationOutcomeUnknownError:
                    self._retire_after_failure(require_explicit_reconnect=False)
                    raise
                except ToyopucProtocolError:
                    if script.completed:
                        self._retire_after_failure(require_explicit_reconnect=False)
                    raise
                finally:
                    self._client._async_transport_script = None
                if pending is None:
                    return result
                payload = pending.payload
                state_changing = pending.state_changing
                frame = await self._exchange(payload, state_changing, deadline, generation)
                script.completed.append(_CompletedExchange(payload, state_changing, frame))

    async def _exchange(
        self,
        payload: bytes,
        state_changing: bool,
        deadline: float,
        generation: int,
    ) -> bytes:
        if generation != self._generation:
            raise ToyopucClosedError("Operation was interrupted by close()")
        if self._explicit_reconnect_required:
            raise ToyopucNotConnectedError("The cancelled or closed session requires an explicit connect()")
        sent = False
        try:
            if self._socket is None:
                await self._open_socket(deadline, generation)
            sock = self._socket
            assert sock is not None
            self._client._last_tx = payload
            self._client._last_rx = None
            self._client._fire_trace(ToyopucTraceDirection.SEND, payload)
            sent = True
            loop = asyncio.get_running_loop()
            await self._await_until_deadline(loop.sock_sendall(sock, payload), deadline)
            self._client._request_count += 1
            self._client._tx_bytes += len(payload)
            if self._client.transport == "tcp":
                header = await self._await_until_deadline(self._recv_exact(sock, 4), deadline)
                length = header[2] | (header[3] << 8)
                frame = header + await self._await_until_deadline(self._recv_exact(sock, length), deadline)
            else:
                frame = await self._await_until_deadline(loop.sock_recv(sock, _UDP_RECEIVE_BUFFER_SIZE), deadline)
            if generation != self._generation:
                raise ToyopucClosedError("Operation was interrupted by close()")
            self._client._last_rx = bytes(frame)
            self._client._rx_bytes += len(frame)
            self._client._fire_trace(ToyopucTraceDirection.RECEIVE, bytes(frame))
            return bytes(frame)
        except asyncio.CancelledError as exc:
            self._mark_udp_tainted(sent)
            self._retire_after_failure(require_explicit_reconnect=True)
            if state_changing and sent:
                raise ToyopucOperationOutcomeUnknownError(
                    ToyopucOutcomeUnknownReason.CANCELLATION,
                    "State-changing request may have reached the PLC before cancellation",
                    cause=exc,
                ) from exc
            raise
        except asyncio.TimeoutError as exc:
            self._mark_udp_tainted(sent)
            self._retire_after_failure(require_explicit_reconnect=False)
            if state_changing and sent:
                raise ToyopucOperationOutcomeUnknownError(
                    ToyopucOutcomeUnknownReason.TIMEOUT,
                    "State-changing request may have reached the PLC before timeout",
                    cause=exc,
                ) from exc
            raise ToyopucTimeoutError("Send/receive timeout") from exc
        except (OSError, EOFError, ToyopucClosedError) as exc:
            closed = generation != self._generation or isinstance(exc, ToyopucClosedError)
            self._mark_udp_tainted(sent)
            self._retire_after_failure(require_explicit_reconnect=closed)
            reason = ToyopucOutcomeUnknownReason.CLOSED if closed else ToyopucOutcomeUnknownReason.TRANSPORT
            if state_changing and sent:
                raise ToyopucOperationOutcomeUnknownError(
                    reason,
                    "State-changing request may have reached the PLC before transport failure",
                    cause=exc,
                ) from exc
            if closed:
                raise ToyopucClosedError("Operation was interrupted by close()") from exc
            raise ToyopucTransportError("Socket error") from exc

    async def _recv_exact(self, sock: socket.socket, count: int) -> bytes:
        data = bytearray(count)
        view = memoryview(data)
        offset = 0
        loop = asyncio.get_running_loop()
        while offset < count:
            chunk = await loop.sock_recv(sock, count - offset)
            if not chunk:
                raise EOFError("TCP connection closed before a complete response")
            view[offset : offset + len(chunk)] = chunk
            offset += len(chunk)
        return bytes(data)

    @staticmethod
    async def _await_until_deadline(awaitable: Awaitable[_T], deadline: float) -> _T:
        remaining = max(0.0, deadline - asyncio.get_running_loop().time())
        return await asyncio.wait_for(awaitable, timeout=remaining)

    async def _open_socket(self, deadline: float, generation: int) -> None:
        loop = asyncio.get_running_loop()
        if self._client._fixed_udp_session_tainted:
            raise ToyopucNotConnectedError("This fixed-port UDP session cannot be reused after an uncertain request")
        last_error: BaseException | None = None
        for attempt in range(int(self._client.retries) + 1):
            candidate: socket.socket | None = None
            try:
                try:
                    literal = ip_address(self._client.host)
                except ValueError:
                    addresses = await self._await_until_deadline(
                        loop.getaddrinfo(
                            self._client.host,
                            self._client.port,
                            family=socket.AF_INET,
                            type=socket.SOCK_STREAM if self._client.transport == "tcp" else socket.SOCK_DGRAM,
                        ),
                        deadline,
                    )
                    if not addresses:
                        raise OSError("Hostname did not resolve to IPv4") from None
                    endpoint = addresses[0][4]
                else:
                    if literal.version != 4:
                        raise OSError("Only IPv4 endpoints are supported")
                    endpoint = (str(literal), self._client.port)
                sock_type = socket.SOCK_STREAM if self._client.transport == "tcp" else socket.SOCK_DGRAM
                candidate = socket.socket(socket.AF_INET, sock_type)
                candidate.setblocking(False)
                if self._client.transport == "tcp":
                    candidate.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                elif self._client.local_port:
                    candidate.bind(("0.0.0.0", int(self._client.local_port)))
                await self._await_until_deadline(loop.sock_connect(candidate, endpoint), deadline)
                if generation != self._generation:
                    raise ToyopucClosedError("Operation was interrupted by close()")
                object.__setattr__(self, "_socket", candidate)
                return
            except asyncio.TimeoutError as exc:
                last_error = exc
            except (OSError, ToyopucClosedError) as exc:
                last_error = exc
                if isinstance(exc, ToyopucClosedError):
                    raise
            finally:
                if candidate is not None and candidate is not self._socket:
                    candidate.close()
            if attempt < int(self._client.retries):
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise ToyopucTimeoutError("Connect timeout") from last_error
                await asyncio.sleep(min(float(self._client.retry_delay), remaining))
        if isinstance(last_error, asyncio.TimeoutError):
            raise ToyopucTimeoutError("Connect timeout") from last_error
        raise ToyopucTransportError("Socket connection failed") from last_error

    def _mark_udp_tainted(self, sent: bool) -> None:
        if sent and self._client.transport == "udp" and self._client.local_port:
            self._client._fixed_udp_session_tainted = True

    def _retire_after_failure(self, *, require_explicit_reconnect: bool) -> None:
        self._close_socket()
        if require_explicit_reconnect:
            object.__setattr__(self, "_explicit_reconnect_required", True)

    def _close_socket(self) -> None:
        sock = self.__dict__.get("_socket")
        object.__setattr__(self, "_socket", None)
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or hasattr(type(self), name):
            object.__setattr__(self, name, value)
            return
        setattr(self._client, name, value)

    async def __aenter__(self) -> _AsyncToyopucClientBase:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.close()


class AsyncToyopucClient(_AsyncToyopucClientBase):
    """Native-async low-level TOYOPUC client."""

    _sync_client_cls = ToyopucClient


class AsyncToyopucDeviceClient(_AsyncToyopucClientBase):
    """Native-async high-level TOYOPUC client."""

    _sync_client_cls = ToyopucDeviceClient

    async def _run_prepared_read_segments_native(self, prepared: Any, result_count: int) -> list[Any]:
        """Execute a fixed aggregate plan once without replaying completed decodes."""

        self._ensure_runtime()
        client = cast(ToyopucDeviceClient, self._client)
        async with self._operation_lock:
            loop = asyncio.get_running_loop()
            deadline = loop.time() + float(client.timeout)
            generation = self._generation
            results: list[Any] = [None] * result_count
            completed = False
            try:
                for segment in prepared:
                    payload = segment.payload if segment.relay is None else segment.relay.outer_payload
                    frame = await self._exchange(payload, False, deadline, generation)
                    completed = True
                    script = _OperationScript()
                    script.completed.append(_CompletedExchange(payload, False, frame))
                    client._async_transport_script = script
                    try:

                        def decode_response(response: Any, current: Any = segment) -> None:
                            client._decode_prepared_read_segment(response, current, results)

                        if segment.relay is None:
                            client._send_and_decode(segment.payload, decode_response)
                        else:
                            client._send_prepared_relay_read_decoded(segment.relay, decode_response)
                    finally:
                        client._async_transport_script = None
                return results
            except ToyopucOperationOutcomeUnknownError:
                self._retire_after_failure(require_explicit_reconnect=False)
                raise
            except ToyopucProtocolError:
                if completed:
                    self._retire_after_failure(require_explicit_reconnect=False)
                raise

    async def read(self, device: Any, count: int) -> list[Any]:
        """Read a contiguous high-level device range with native async transport."""
        _require_positive_count(count)
        client = cast(ToyopucDeviceClient, self._client)
        if type(client) is not ToyopucDeviceClient:
            return await self._run_native_callable(client.read, device, count)
        resolved = client._coerce_device(device)
        devices = client._seq_devices(resolved, count)
        plan = client._get_read_plan(devices, split_pc10=True)
        prepared = client._prepare_read_segments(devices, plan)
        return await self._run_prepared_read_segments_native(prepared, len(devices))

    async def read_devices(self, devices: Any) -> list[Any]:
        """Read sparse high-level devices in caller order with native async transport."""
        client = cast(ToyopucDeviceClient, self._client)
        devices_snapshot = tuple(devices)
        if type(client) is not ToyopucDeviceClient:
            return await self._run_native_callable(client.read_devices, devices_snapshot)
        resolved = [client._coerce_device(device) for device in devices_snapshot]
        plan = client._get_read_plan(resolved, split_pc10=True)
        prepared = client._prepare_read_segments(resolved, plan)
        return await self._run_prepared_read_segments_native(prepared, len(resolved))

    async def relay_read(self, hops: Any, device: Any, count: int) -> list[Any]:
        """Read a contiguous high-level device range through explicit relay hops."""
        _require_positive_count(count)
        client = cast(ToyopucDeviceClient, self._client)
        if type(client) is not ToyopucDeviceClient:
            return await self._run_native_callable(client.relay_read, hops, device, count)
        resolved = client._coerce_device(device)
        devices = client._seq_devices(resolved, count)
        plan = client._get_read_plan(devices, split_pc10=True)
        prepared = client._prepare_read_segments(devices, plan, hops=hops)
        return await self._run_prepared_read_segments_native(prepared, len(devices))

    async def relay_read_devices(self, hops: Any, devices: Any) -> list[Any]:
        """Read sparse high-level devices through explicit relay hops in caller order."""
        client = cast(ToyopucDeviceClient, self._client)
        devices_snapshot = tuple(devices)
        if type(client) is not ToyopucDeviceClient:
            return await self._run_native_callable(client.relay_read_devices, hops, devices_snapshot)
        resolved = [client._coerce_device(device) for device in devices_snapshot]
        plan = client._get_read_plan(resolved, split_pc10=True)
        prepared = client._prepare_read_segments(resolved, plan, hops=hops)
        return await self._run_prepared_read_segments_native(prepared, len(resolved))


_CLIENT_ASYNC_METHODS = [
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
]

_HIGH_LEVEL_ASYNC_METHODS = [
    "resolve_device",
    "relay_read_one",
    "relay_write",
    "relay_read_words",
    "relay_write_words",
    "relay_write_many",
    "read_fr_one",
    "read_fr",
    "relay_read_fr_one",
    "relay_read_fr",
    "write_fr",
    "relay_write_fr",
    "commit_fr",
    "relay_commit_fr",
    "write_fr_work_area",
    "relay_write_fr_work_area",
    "commit_fr_block_by_device",
    "relay_commit_fr_block_by_device",
    "read_one",
    "write",
    "write_many",
    "write_bit_in_word",
    "relay_write_bit_in_word",
    "read_program_timer_counter_values",
    "write_program_timer_counter_values",
    "write_program_timer_counter_preset",
    "write_program_timer_counter_current",
    "relay_read_program_timer_counter_values",
    "relay_write_program_timer_counter_values",
    "relay_write_program_timer_counter_preset",
    "relay_write_program_timer_counter_current",
    "read_dword",
    "write_dword",
    "read_dwords",
    "write_dwords",
    "read_float32",
    "write_float32",
    "read_float32s",
    "write_float32s",
    "relay_read_dword",
    "relay_write_dword",
    "relay_read_dwords",
    "relay_write_dwords",
    "relay_read_float32",
    "relay_write_float32",
    "relay_read_float32s",
    "relay_write_float32s",
]

for _method_name in _CLIENT_ASYNC_METHODS:
    _install_async_wrapper(AsyncToyopucClient, _method_name)
    _install_async_wrapper(AsyncToyopucDeviceClient, _method_name)

for _method_name in _HIGH_LEVEL_ASYNC_METHODS:
    _install_async_wrapper(AsyncToyopucDeviceClient, _method_name)
