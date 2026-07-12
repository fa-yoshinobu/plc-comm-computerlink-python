import asyncio
from threading import Event
from types import SimpleNamespace

import pytest

from toyopuc import (
    AsyncToyopucDeviceClient,
    ToyopucClient,
    ToyopucConnectionOptions,
    ToyopucDeviceClient,
    ToyopucProtocolError,
    encode_word_address,
    format_device_address,
    normalize_address,
    open_and_connect,
    parse_address,
    parse_device_address,
    read_dwords_single_request,
    read_named,
    read_typed,
    read_words_single_request,
    try_parse_device_address,
    write_dwords_single_request,
    write_typed,
    write_words_single_request,
)
from toyopuc.protocol import build_fr_register

GENERIC_PROFILE = "toyopuc:generic"


def _word_addr(text: str) -> int:
    return encode_word_address(parse_address(text, "word"))


class _DummyWordClient(ToyopucClient):
    def __init__(self) -> None:
        super().__init__("127.0.0.1", 1025, transport="tcp")
        self.next_words: list[int] = []
        self.word_reads: list[tuple[int, int]] = []
        self.word_writes: list[tuple[int, list[int]]] = []

    def read_words(self, addr: int, count: int):
        self.word_reads.append((addr, count))
        result = self.next_words[:count]
        self.next_words = self.next_words[count:]
        return result

    def write_words(self, addr: int, values):
        self.word_writes.append((addr, list(values)))


class _DummyHighLevelClient(ToyopucDeviceClient):
    def __init__(self) -> None:
        super().__init__("127.0.0.1", 1025, transport="tcp", plc_profile=GENERIC_PROFILE)
        self.word_map: dict[int, int] = {}
        self.word_reads: list[tuple[int, int]] = []
        self.word_writes: list[tuple[int, list[int]]] = []

    def read_words(self, addr: int, count: int):
        self.word_reads.append((addr, count))
        return [self.word_map[addr + offset] for offset in range(count)]

    def write_words(self, addr: int, values):
        self.word_writes.append((addr, list(values)))


class _DummyAsyncHighLevelClient(AsyncToyopucDeviceClient):
    def __init__(self) -> None:
        object.__setattr__(self, "_client", _DummyHighLevelClient())


class _DummyUtilitySyncClient:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}

    def read_one(self, device: str) -> int:
        return self.values[device]


class _DummyAsyncUtilityClient(AsyncToyopucDeviceClient):
    def __init__(self) -> None:
        object.__setattr__(self, "_client", _DummyUtilitySyncClient())


class _DummySurfaceSyncClient(_DummyHighLevelClient):
    def __init__(self) -> None:
        super().__init__()
        self.read_dword_map: dict[str, list[int]] = {}
        self.write_dword_calls: list[tuple[str, list[int]]] = []

    def resolve_device(self, device: str):
        return super().resolve_device(device)

    def read_dwords(self, device: int | str, count: int):
        assert isinstance(device, str)
        return self.read_dword_map[device][:count]

    def write_dwords(self, device: int | str, values):
        assert isinstance(device, str)
        self.write_dword_calls.append((device, list(values)))


class _DummyAsyncSurfaceClient(AsyncToyopucDeviceClient):
    def __init__(self) -> None:
        object.__setattr__(self, "_client", _DummySurfaceSyncClient())

    async def _run_sync_in_worker(self, func, /, *args, **kwargs):
        return func(*args, **kwargs)


class _NoIoHighLevelClient(ToyopucDeviceClient):
    def __init__(self) -> None:
        super().__init__("127.0.0.1", 1025, transport="tcp", plc_profile=GENERIC_PROFILE)
        self.send_count = 0

    def _send_and_recv(self, payload: bytes, *, retryable: bool = False):
        self.send_count += 1
        raise AssertionError("validation must reject before transport")


class _NoIoAsyncHighLevelClient(AsyncToyopucDeviceClient):
    def __init__(self) -> None:
        object.__setattr__(self, "_client", _NoIoHighLevelClient())

    async def _run_sync_in_worker(self, func, /, *args, **kwargs):
        return func(*args, **kwargs)


class _CommitCaptureClient(ToyopucDeviceClient):
    def __init__(self) -> None:
        super().__init__("127.0.0.1", 1025, transport="tcp", plc_profile=GENERIC_PROFILE)
        self.payloads: list[bytes] = []

    def _send_and_recv(self, payload: bytes, *, retryable: bool = False):
        self.payloads.append(payload)
        return SimpleNamespace(cmd=0xCA)


def test_low_level_32bit_helpers_use_low_word_first() -> None:
    client = _DummyWordClient()
    client.next_words = [0x5678, 0x1234]
    assert client.read_dword(0x1100) == 0x12345678

    client.next_words = [0x0000, 0x3FC0]
    assert client.read_float32(0x1100) == pytest.approx(1.5)

    client.write_dword(0x1100, 0x12345678)
    assert client.word_writes[-1] == (0x1100, [0x5678, 0x1234])

    client.write_float32(0x1100, 1.5)
    assert client.word_writes[-1] == (0x1100, [0x0000, 0x3FC0])


def test_high_level_32bit_helpers_use_word_sequences() -> None:
    client = _DummyHighLevelClient()
    addr0 = _word_addr("B0000")
    addr1 = _word_addr("B0001")
    client.word_map = {addr0: 0x5678, addr1: 0x1234}

    assert client.read_dword("B0000") == 0x12345678
    # Batch optimization: consecutive words are fetched in one read_words(addr, 2) call
    assert client.word_reads == [(addr0, 2)]

    client.write_float32("B0000", 1.5)
    # Batch optimization: consecutive word write in one write_words(addr, [lo, hi]) call
    assert client.word_writes == [(addr0, [0x0000, 0x3FC0])]


def test_async_high_level_helpers_wrap_sync_implementation() -> None:
    client = _DummyAsyncHighLevelClient()
    addr0 = _word_addr("B0000")
    addr1 = _word_addr("B0001")
    client.word_map = {addr0: 0x5678, addr1: 0x1234}

    async def run_checks() -> None:
        assert await client.read_dword("B0000") == 0x12345678
        await client.write_float32("B0000", 1.5)

    asyncio.run(run_checks())

    assert client.word_reads == [(addr0, 2)]
    assert client.word_writes == [(addr0, [0x0000, 0x3FC0])]


def test_read_named_supports_hex_bit_indices() -> None:
    client = _DummyAsyncUtilityClient()
    client.values = {"B0000": (1 << 10) | (1 << 13) | (1 << 15)}

    async def run_checks() -> None:
        assert await read_named(client, ["B0000.A"]) == {"B0000.A": True}
        assert await read_named(client, ["B0000.D"]) == {"B0000.D": True}
        assert await read_named(client, ["B0000.F"]) == {"B0000.F": True}

    asyncio.run(run_checks())


def test_read_named_rejects_multiple_addresses() -> None:
    client = _DummyAsyncUtilityClient()
    client.values = {"B0000": 0}

    async def run_checks() -> None:
        with pytest.raises(ToyopucProtocolError, match="one named address"):
            await read_named(client, ["B0000:A", "B0001:A"])

    asyncio.run(run_checks())


def test_read_named_rejects_invalid_bit_index() -> None:
    client = _DummyAsyncUtilityClient()
    client.values = {"B0000": 0}

    async def run_checks() -> None:
        with pytest.raises(ValueError):
            await read_named(client, ["B0000.10"])
        with pytest.raises(ValueError, match="explicit bit index"):
            await read_named(client, ["B0000:BIT_IN_WORD"])

    asyncio.run(run_checks())


def test_normalize_address_uses_profile_rules() -> None:
    assert normalize_address("p1-d0000", profile="toyopuc:plus:extended") == "P1-D0000"


def test_public_device_address_helpers_parse_and_format() -> None:
    typed = parse_device_address("p1-d0100:f", profile="toyopuc:generic")
    bit = parse_device_address("p1-d0100.a", profile="toyopuc:generic")
    bit_d = parse_device_address("p1-d0100.d", profile="toyopuc:generic")

    assert typed.text == "P1-D0100:F"
    assert typed.base_device == "P1-D0100"
    assert typed.dtype == "F"
    assert typed.bit_index is None
    assert bit.text == "P1-D0100.A"
    assert bit.base_device == "P1-D0100"
    assert bit.dtype == "BIT_IN_WORD"
    assert bit.bit_index == 10
    assert bit_d.text == "P1-D0100.D"
    assert bit_d.base_device == "P1-D0100"
    assert bit_d.dtype == "BIT_IN_WORD"
    assert bit_d.bit_index == 13
    assert format_device_address(typed) == "P1-D0100:F"
    assert format_device_address(bit) == "P1-D0100.A"
    assert format_device_address(bit_d) == "P1-D0100.D"
    assert format_device_address("p1-d0100:s", profile="toyopuc:generic") == "P1-D0100:S"


def test_public_device_address_helpers_return_none_on_invalid_input() -> None:
    assert try_parse_device_address("P1-D10000", profile="toyopuc:plus:standard") is None
    assert try_parse_device_address("P1-D0100.10", profile="toyopuc:generic") is None
    assert try_parse_device_address("P1-D0100:BIT_IN_WORD", profile="toyopuc:generic") is None


def test_named_addresses_require_explicit_dtype_and_preserve_dot_d_bit_meaning() -> None:
    with pytest.raises(ValueError, match="requires explicit dtype"):
        parse_device_address("P1-D0100", profile=GENERIC_PROFILE)
    assert parse_device_address("P1-D0100:U", profile=GENERIC_PROFILE).text == "P1-D0100:U"
    assert parse_device_address("P1-D0100:D", profile=GENERIC_PROFILE).dtype == "D"
    bit = parse_device_address("P1-D0100.D", profile=GENERIC_PROFILE)
    assert bit.dtype == "BIT_IN_WORD"
    assert bit.bit_index == 13


def test_typed_helpers_reject_unknown_dtype_and_out_of_range_values() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.read_value = 0
            self.writes: list[tuple[str, object]] = []

        async def read_one(self, device: str) -> int:
            return self.read_value

        async def write(self, device: str, value: int) -> None:
            self.writes.append((device, value))

        async def read_dwords(self, device: str, count: int) -> list[int]:
            return [self.read_value]

        async def write_dwords(self, device: str, values: list[int]) -> None:
            self.writes.append((device, values))

        async def read_float32s(self, device: str, count: int) -> list[float]:
            return [float(self.read_value)]

        async def write_float32s(self, device: str, values: list[float]) -> None:
            self.writes.append((device, values))

    async def run() -> None:
        client = FakeClient()
        with pytest.raises(ValueError, match="Unsupported dtype"):
            await read_typed(client, "P1-D0100", "UNKNOWN")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="Unsupported dtype"):
            await write_typed(client, "P1-D0100", "UNKNOWN", 1)  # type: ignore[arg-type]
        for dtype, value in [("U", -1), ("U", 65_536), ("S", -32_769), ("D", 0x100000000), ("L", 0x80000000)]:
            with pytest.raises(ValueError, match="range"):
                await write_typed(client, "P1-D0100", dtype, value)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="integer"):
            await write_typed(client, "P1-D0100", "U", 1.5)  # type: ignore[arg-type]
        assert client.writes == []

        client.read_value = 65_536
        with pytest.raises(ToyopucProtocolError, match="outside"):
            await read_typed(client, "P1-D0100", "U")  # type: ignore[arg-type]

    asyncio.run(run())


def test_connection_options_requires_explicit_profile() -> None:
    with pytest.raises(TypeError):
        ToyopucConnectionOptions("127.0.0.1")


def test_connection_options_validates_factory_level_network_options() -> None:
    with pytest.raises(ValueError, match="Host must not be empty"):
        ToyopucConnectionOptions(" ", 1025, "tcp", GENERIC_PROFILE)
    with pytest.raises(ValueError, match="Port must be in the range 1-65535"):
        ToyopucConnectionOptions("127.0.0.1", 0, "tcp", GENERIC_PROFILE)
    with pytest.raises(ValueError, match="Port must be in the range 1-65535"):
        ToyopucConnectionOptions("127.0.0.1", 65_536, "tcp", GENERIC_PROFILE)
    with pytest.raises(ValueError, match="LocalPort must be in the range 0-65535"):
        ToyopucConnectionOptions("127.0.0.1", 1025, "udp", GENERIC_PROFILE, local_port=-1)
    with pytest.raises(ValueError, match="LocalPort must be in the range 0-65535"):
        ToyopucConnectionOptions("127.0.0.1", 1025, "udp", GENERIC_PROFILE, local_port=65_536)
    with pytest.raises(ValueError, match="only valid for UDP"):
        ToyopucConnectionOptions("127.0.0.1", 1025, "tcp", GENERIC_PROFILE, local_port=12345)
    with pytest.raises(ValueError, match="positive finite"):
        ToyopucConnectionOptions("127.0.0.1", 1025, "tcp", GENERIC_PROFILE, timeout=0)
    with pytest.raises(ValueError, match="non-negative integer"):
        ToyopucConnectionOptions("127.0.0.1", 1025, "tcp", GENERIC_PROFILE, retries=True)
    with pytest.raises(ValueError, match="non-negative finite"):
        ToyopucConnectionOptions("127.0.0.1", 1025, "tcp", GENERIC_PROFILE, retry_delay=float("nan"))


def test_connection_options_defaults() -> None:
    options = ToyopucConnectionOptions("127.0.0.1", 1025, "tcp", GENERIC_PROFILE)
    assert options.port == 1025
    assert options.local_port == 0
    assert options.transport == "tcp"
    assert options.timeout == 3.0
    assert options.retries == 0
    assert options.retry_delay == 0.2
    assert options.plc_profile == GENERIC_PROFILE


def test_open_and_connect_accepts_options(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int, dict[str, object]]] = []

    class _FakeAsyncClient:
        def __init__(self, host: str, port: int, **kwargs: object) -> None:
            calls.append((host, port, kwargs))

        async def connect(self) -> None:
            return None

    monkeypatch.setattr("toyopuc.async_client.AsyncToyopucDeviceClient", _FakeAsyncClient, raising=False)

    async def run() -> None:
        client = await open_and_connect(ToyopucConnectionOptions("127.0.0.1", 1025, "tcp", GENERIC_PROFILE, retries=2))
        assert isinstance(client, _FakeAsyncClient)

    asyncio.run(run())
    assert calls == [
        (
            "127.0.0.1",
            1025,
            {
                "local_port": 0,
                "transport": "tcp",
                "timeout": 3.0,
                "retries": 2,
                "retry_delay": 0.2,
                "plc_profile": GENERIC_PROFILE,
            },
        )
    ]


def test_explicit_word_and_dword_surface() -> None:
    client = _DummyAsyncSurfaceClient()
    addr0 = _word_addr("B0000")
    addr1 = _word_addr("B0001")
    addr2 = _word_addr("B0002")
    addr3 = _word_addr("B0003")
    client.word_map = {addr0: 1, addr1: 2, addr2: 3, addr3: 4}
    client.read_dword_map = {"B0000": [0x12345678], "B0002": [0xCAFEBABE]}

    async def run_checks() -> None:
        assert await read_words_single_request(client, "B0000", 2) == [1, 2]
        assert await read_dwords_single_request(client, "B0000", 1) == [0x12345678]
        await write_words_single_request(client, "B0000", [10, 11])
        await write_dwords_single_request(client, "B0000", [0x12345678])

    asyncio.run(run_checks())

    assert client.word_writes == [
        (addr0, [10, 11]),
    ]
    assert client.write_dword_calls == [
        ("B0000", [0x12345678]),
    ]


def test_read_one_and_contiguous_read_have_stable_return_shapes() -> None:
    client = _DummyHighLevelClient()
    addr = _word_addr("B0000")
    client.word_map = {addr: 0x1234}

    assert client.read_one("B0000") == 0x1234
    assert client.read("B0000", 1) == [0x1234]
    with pytest.raises(TypeError):
        client.read("B0000")  # type: ignore[call-arg]
    for invalid in (True, 0, -1, 1.5):
        with pytest.raises(ValueError, match="integer >= 1"):
            client.read("B0000", invalid)  # type: ignore[arg-type]


def test_single_request_ranges_reject_boundaries_and_limits_before_transport() -> None:
    client = _NoIoHighLevelClient()

    with pytest.raises(ToyopucProtocolError, match="one compatible protocol request"):
        client.read("FR007FFF", 2)
    with pytest.raises(ToyopucProtocolError, match="one compatible protocol request"):
        client.read_dwords("FR007FFF", 1)
    with pytest.raises(ToyopucProtocolError, match="one compatible protocol request"):
        client.write_dwords("FR007FFF", [0x12345678])
    with pytest.raises(ValueError, match="CMD=1C word-read"):
        client.read("B0000", 513)

    assert client.send_count == 0


def test_dword_and_float_array_counts_are_strict() -> None:
    client = _NoIoHighLevelClient()
    for invalid in (True, 0, -1, 1.5):
        with pytest.raises(ValueError, match="integer >= 1"):
            client.read_dwords("B0000", invalid)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="integer >= 1"):
            client.read_float32s("B0000", invalid)  # type: ignore[arg-type]
    assert client.send_count == 0


def test_fr_work_area_write_and_commit_are_separate_single_requests() -> None:
    client = _CommitCaptureClient()

    client.commit_fr("FR000000")
    assert client.payloads == [build_fr_register(0x40)]

    invalid = _NoIoHighLevelClient()
    with pytest.raises(ValueError, match="first word"):
        invalid.commit_fr("FR000001")
    with pytest.raises(ValueError, match="within one"):
        invalid.write_fr("FR007FFF", [1, 2])
    with pytest.raises(ValueError, match="single-request limit"):
        invalid.write_fr("FR000000", [0] * 505)
    assert invalid.send_count == 0


@pytest.mark.parametrize("value", [-1, 0x10000, True, 1.5, "1"])
def test_fr_work_area_write_rejects_values_that_would_be_coerced_or_masked(value: object) -> None:
    direct = _NoIoHighLevelClient()
    with pytest.raises(ValueError, match="FR word values must be integers in the range 0..65535"):
        direct.write_fr("FR000000", value)
    assert direct.send_count == 0

    relay = _NoIoHighLevelClient()
    with pytest.raises(ValueError, match="FR word values must be integers in the range 0..65535"):
        relay.relay_write_fr("P1-L2:N2", "FR000000", value)
    assert relay.send_count == 0


@pytest.mark.parametrize("value", [-1, 0x10000, True, 1.5, "1"])
def test_async_fr_work_area_write_rejects_values_before_transport(value: object) -> None:
    direct = _NoIoAsyncHighLevelClient()
    relay = _NoIoAsyncHighLevelClient()

    async def run_checks() -> None:
        with pytest.raises(ValueError, match="FR word values must be integers in the range 0..65535"):
            await direct.write_fr("FR000000", value)
        with pytest.raises(ValueError, match="FR word values must be integers in the range 0..65535"):
            await relay.relay_write_fr("P1-L2:N2", "FR000000", value)

    asyncio.run(run_checks())
    assert direct._client.send_count == 0
    assert relay._client.send_count == 0


def test_removed_fr_combined_and_range_surfaces_are_not_public() -> None:
    client = _NoIoHighLevelClient()
    for name in (
        "write_fr_words_ex",
        "write_fr_words_committed",
        "commit_fr_range",
        "wait_fr_write_complete",
        "relay_write_fr_words_ex",
        "relay_commit_fr_range",
        "relay_wait_fr_write_complete",
        "fr_register",
        "relay_fr_register",
    ):
        assert not hasattr(client, name)


def test_async_cancellation_stops_worker_before_returning() -> None:
    client = AsyncToyopucDeviceClient(
        "127.0.0.1",
        1025,
        transport="tcp",
        plc_profile=GENERIC_PROFILE,
    )
    started = Event()

    def blocking_operation() -> None:
        started.set()
        client._client._cancel_event.wait()
        client._client._raise_if_cancelled()

    async def run() -> None:
        task = asyncio.create_task(client._run_sync_in_worker(blocking_operation))
        await asyncio.to_thread(started.wait, 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not client._client._cancel_event.is_set()
        assert await client._run_sync_in_worker(lambda: 42) == 42

    asyncio.run(run())
