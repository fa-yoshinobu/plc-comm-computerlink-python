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
    encode_fr_word_addr32,
    encode_word_address,
    format_device_address,
    normalize_address,
    open_and_connect,
    parse_address,
    parse_device_address,
    poll,
    read_dwords_single_request,
    read_named,
    read_typed,
    read_words_single_request,
    try_parse_device_address,
    write_bit_in_word,
    write_dwords_single_request,
    write_typed,
    write_words_single_request,
)
from toyopuc.protocol import build_fr_register, build_pc10_block_write

GENERIC_PROFILE = "toyopuc:generic"
MAX_TIMER_SECONDS = 2_147_483.647


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


class _DummyUtilitySyncClient(_DummyHighLevelClient):
    def __init__(self) -> None:
        super().__init__()

    @property
    def values(self) -> dict[str, int]:
        return {}

    @values.setter
    def values(self, values: dict[str, int]) -> None:
        self.word_map = {_word_addr(address): value for address, value in values.items()}


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

    def _send_and_recv(self, payload: bytes, *, state_changing: bool = False):
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

    def _send_and_recv(self, payload: bytes, *, state_changing: bool = False):
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


@pytest.mark.parametrize(
    "interval",
    [
        0,
        -1,
        float("nan"),
        float("inf"),
        True,
        "1",
        MAX_TIMER_SECONDS + 0.001,
        pytest.param(10**10_000, id="huge-int"),
    ],
)
def test_poll_rejects_invalid_interval_before_io(interval: object) -> None:
    async def run() -> None:
        iterator = poll(object(), ["P1-D0000"], interval)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="positive finite"):
            await anext(iterator)

    asyncio.run(run())


def test_poll_accepts_the_common_timer_boundary_without_starting_the_delay() -> None:
    async def run() -> None:
        client = _DummyAsyncUtilityClient()
        client.values = {"B0000": 0x1234}
        iterator = poll(client, ["B0000:U"], MAX_TIMER_SECONDS)
        assert await anext(iterator) == {"B0000:U": 0x1234}
        assert client.word_reads == [(_word_addr("B0000"), 1)]
        await iterator.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("value", [0, 1, 2, -1, "false", [], None])
def test_write_bit_in_word_rejects_every_non_bool_before_io(value: object) -> None:
    class NoIoClient:
        read_calls = 0
        write_calls = 0

        async def read_one(self, _device: str) -> int:
            self.read_calls += 1
            return 0

        async def write(self, _device: str, _value: int) -> None:
            self.write_calls += 1

    async def run() -> None:
        client = NoIoClient()
        with pytest.raises(ValueError, match="must be bool"):
            await write_bit_in_word(client, "P1-D0000", 0, value)  # type: ignore[arg-type]
        assert client.read_calls == 0
        assert client.write_calls == 0

    asyncio.run(run())


@pytest.mark.parametrize("value", [0, 1])
def test_high_level_bit_writes_reject_integer_bits_before_transport(value: int) -> None:
    client = _NoIoHighLevelClient()

    with pytest.raises(ValueError, match="must be bool"):
        client.write("P1-M0000", value)
    with pytest.raises(ValueError, match="must be bool"):
        client.write_many({"P1-M0000": value})
    with pytest.raises(ValueError, match="must be bool"):
        client.relay_write("P1-L2:N2", "P1-M0000", value)
    with pytest.raises(ValueError, match="must be bool"):
        client.relay_write_many("P1-L2:N2", {"P1-M0000": value})

    assert client.send_count == 0


@pytest.mark.parametrize("bit_index", [True, -1, 16, 1.5, "1"])
def test_write_bit_in_word_rejects_invalid_bit_index_before_io(bit_index: object) -> None:
    class NoIoClient:
        read_calls = 0

        async def read_one(self, _device: str) -> int:
            self.read_calls += 1
            return 0

    async def run() -> None:
        client = NoIoClient()
        with pytest.raises(ValueError, match="bit_index must be 0-15"):
            await write_bit_in_word(client, "P1-D0000", bit_index, True)  # type: ignore[arg-type]
        assert client.read_calls == 0

    asyncio.run(run())


def test_write_many_rejects_aliases_for_the_same_wire_address_before_transport() -> None:
    client = _NoIoHighLevelClient()

    with pytest.raises(ToyopucProtocolError):
        client.write_many({"P1-D0": 1, "P1-D0000": 2})

    assert client.send_count == 0


@pytest.mark.parametrize("value", [-1, 0x100000000, True, 1.5, "1"])
def test_dword_writes_reject_coercion_before_transport(value: object) -> None:
    client = _NoIoHighLevelClient()

    with pytest.raises(ValueError):
        client.write_dwords("FR000000", [value])  # type: ignore[list-item]

    assert client.send_count == 0


def test_all_named_fr_generic_and_typed_writes_reject_before_transport() -> None:
    client = _NoIoHighLevelClient()
    for device in ("FR000000", client.resolve_device("FR000000")):
        operations = [
            lambda device=device: client.write(device, 1),
            lambda device=device: client.write_many({device: 1}),
            lambda device=device: client.relay_write("P1-L2:N2", device, 1),
            lambda device=device: client.relay_write_many("P1-L2:N2", {device: 1}),
            lambda device=device: client.write_dword(device, 1),
            lambda device=device: client.write_float32(device, 1.0),
            lambda device=device: client.relay_write_dword("P1-L2:N2", device, 1),
            lambda device=device: client.relay_write_float32("P1-L2:N2", device, 1.0),
        ]
        for operation in operations:
            with pytest.raises(ValueError, match="Generic FR writes are disabled"):
                operation()
    assert client.send_count == 0


def test_async_utilities_reject_named_fr_before_any_read_or_write() -> None:
    client = _NoIoAsyncHighLevelClient()

    async def run_checks() -> None:
        resolved = client._client.resolve_device("FR000000")
        for device in ("FR000000", resolved):
            operations = [
                client.write(device, 1),
                client.write_many({device: 1}),
                client.write_dwords(device, [1]),
                client.write_float32s(device, [1.0]),
                client.relay_write("P1-L2:N2", device, 1),
                client.relay_write_many("P1-L2:N2", {device: 1}),
                client.relay_write_dwords("P1-L2:N2", device, [1]),
                client.relay_write_float32s("P1-L2:N2", device, [1.0]),
            ]
            for operation in operations:
                with pytest.raises(ValueError, match="Generic FR writes are disabled"):
                    await operation

        utility_operations = [
            write_words_single_request(client, "FR000000", [1]),
            write_dwords_single_request(client, "FR000000", [1]),
            write_typed(client, "FR000000", "F", 1.0),
            write_bit_in_word(client, "FR000000", 0, True),
        ]
        for operation in utility_operations:
            with pytest.raises(ValueError, match="Generic FR writes are disabled"):
                await operation

    asyncio.run(run_checks())
    assert client._client.send_count == 0


@pytest.mark.parametrize(
    ("device", "value"),
    [
        ("M0000", 2),
        ("M0000", "1"),
        ("B0000", -1),
        ("B0000", 0x10000),
        ("U0000L", 256),
        ("B0000", True),
        ("B0000", 1.5),
    ],
)
def test_generic_writes_reject_masking_and_coercion_before_transport(device: str, value: object) -> None:
    client = _NoIoHighLevelClient()

    with pytest.raises(ValueError):
        client.write(device, value)

    assert client.send_count == 0


def test_sequence_write_uses_one_batch_request_and_empty_collections_fail() -> None:
    client = _DummyHighLevelClient()

    client.write("B0000", [1, 2, 3])

    assert len(client.word_writes) == 1
    assert client.word_writes[0][1] == [1, 2, 3]
    with pytest.raises(ValueError):
        client.read_devices([])
    with pytest.raises(ValueError):
        client.write_many({})
    with pytest.raises(ValueError):
        client.relay_read_devices("P1-L2:N2", [])
    with pytest.raises(ValueError):
        client.relay_write_many("P1-L2:N2", {})

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


def test_read_named_aggregates_multiple_addresses_in_declaration_order() -> None:
    client = _DummyAsyncUtilityClient()
    client.values = {"B0000": 1, "B0001": 0xFFFF}

    async def run_checks() -> None:
        result = await read_named(client, ["B0000:U", "B0001:S"])
        assert list(result) == ["B0000:U", "B0001:S"]
        assert result == {"B0000:U": 1, "B0001:S": -1}

    asyncio.run(run_checks())
    assert client.word_reads == [(_word_addr("B0000"), 2)]


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


def test_connection_options_enforce_the_common_timer_boundary() -> None:
    options = ToyopucConnectionOptions(
        "127.0.0.1",
        1025,
        "tcp",
        GENERIC_PROFILE,
        timeout=MAX_TIMER_SECONDS,
        retry_delay=MAX_TIMER_SECONDS,
    )
    assert options.timeout == MAX_TIMER_SECONDS
    assert options.retry_delay == MAX_TIMER_SECONDS

    with pytest.raises(ValueError, match="no greater than 2147483.647 seconds"):
        ToyopucConnectionOptions(
            "127.0.0.1",
            1025,
            "tcp",
            GENERIC_PROFILE,
            timeout=MAX_TIMER_SECONDS + 0.001,
        )
    with pytest.raises(ValueError, match="no greater than 2147483.647 seconds"):
        ToyopucConnectionOptions(
            "127.0.0.1",
            1025,
            "tcp",
            GENERIC_PROFILE,
            retry_delay=MAX_TIMER_SECONDS + 0.001,
        )


@pytest.mark.parametrize("host", ["::1", "[::1]", "::ffff:127.0.0.1"])
def test_connection_options_reject_ipv6_literals(host: str) -> None:
    with pytest.raises(ValueError, match="must be an IPv4 address"):
        ToyopucConnectionOptions(host, 1025, "tcp", GENERIC_PROFILE)


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

    fr_start = client.resolve_device("FR007FFF")
    fr_devices = client._seq_devices(fr_start, 2)
    assert client._get_read_plan(fr_devices, split_pc10=True) == (1, 1)

    basic_start = client.resolve_device("B0000")
    basic_devices = client._seq_devices(basic_start, 513)
    assert client._get_read_plan(basic_devices, split_pc10=True) == (512, 1)

    with pytest.raises(ToyopucProtocolError, match="declared read entry"):
        client.read_dwords("FR007FFF", 1)
    with pytest.raises(ValueError, match="Generic FR writes are disabled"):
        client.write_dwords("FR007FFF", [0x12345678])

    assert client.send_count == 0


def test_read_aggregate_splits_only_as_needed_and_returns_all_values_in_order() -> None:
    class AggregateCaptureClient(ToyopucDeviceClient):
        def __init__(self) -> None:
            super().__init__("127.0.0.1", 1025, transport="tcp", plc_profile=GENERIC_PROFILE)
            self.batches: list[list[str]] = []

        def _read_batch(self, devices):
            self.batches.append([device.text for device in devices])
            return [device.index for device in devices]

    client = AggregateCaptureClient()
    values = client.read("B0000", 513)

    assert values == list(range(513))
    assert list(map(len, client.batches)) == [512, 1]


def test_read_aggregate_preflights_every_request_before_first_transport() -> None:
    class PreflightFailureClient(ToyopucDeviceClient):
        def __init__(self) -> None:
            super().__init__("127.0.0.1", 1025, transport="tcp", plc_profile=GENERIC_PROFILE)
            self.preflight_count = 0
            self.read_count = 0

        def _preflight_read_batch(self, devices):
            self.preflight_count += 1
            if self.preflight_count == 2:
                raise ValueError("injected second-plan failure")
            return super()._preflight_read_batch(devices)

        def _read_batch(self, devices):
            self.read_count += 1
            return [0] * len(devices)

    client = PreflightFailureClient()
    with pytest.raises(ValueError, match="second-plan"):
        client.read_devices(["B0000", "P1-D0000"])

    assert client.preflight_count == 2
    assert client.read_count == 0


def test_bit_in_word_rmw_runs_read_and_write_in_one_exclusive_turn() -> None:
    class RmwClient(ToyopucDeviceClient):
        def __init__(self) -> None:
            super().__init__("127.0.0.1", 1025, transport="tcp", plc_profile=GENERIC_PROFILE)
            self.depths: list[int] = []
            self.written: int | None = None

        def read_one(self, device):
            self.depths.append(self._operation_context.depth)
            return 0

        def write(self, device, value):
            self.depths.append(self._operation_context.depth)
            self.written = value

    async def run() -> None:
        wrapper = AsyncToyopucDeviceClient.__new__(AsyncToyopucDeviceClient)
        object.__setattr__(wrapper, "_client", RmwClient())
        await write_bit_in_word(wrapper, "B0000", 3, True)
        assert wrapper._client.depths == [1, 1]
        assert wrapper._client.written == 8

    asyncio.run(run())


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

    client.write_fr("FR000000", [0x1234, 0x5678])
    assert client.payloads == [
        build_pc10_block_write(
            encode_fr_word_addr32(0),
            bytes.fromhex("34127856"),
        )
    ]

    client.commit_fr("FR000000")
    assert client.payloads == [
        build_pc10_block_write(encode_fr_word_addr32(0), bytes.fromhex("34127856")),
        build_fr_register(0x40),
    ]

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
