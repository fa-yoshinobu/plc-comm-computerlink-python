import asyncio

import pytest

from toyopuc import (
    AsyncToyopucDeviceClient,
    ToyopucClient,
    ToyopucConnectionOptions,
    ToyopucDeviceClient,
    encode_word_address,
    format_device_address,
    normalize_address,
    open_and_connect,
    parse_address,
    parse_device_address,
    read_dwords_chunked,
    read_dwords_single_request,
    read_named,
    read_words_chunked,
    read_words_single_request,
    try_parse_device_address,
    write_dwords_chunked,
    write_dwords_single_request,
    write_words_chunked,
    write_words_single_request,
)


def _word_addr(text: str) -> int:
    return encode_word_address(parse_address(text, "word"))


class _DummyWordClient(ToyopucClient):
    def __init__(self) -> None:
        super().__init__("127.0.0.1", 1025)
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
        super().__init__("127.0.0.1", 1025)
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

    def read(self, device: str, count: int = 1) -> int:
        assert count == 1
        return self.values[device]


class _DummyAsyncUtilityClient(AsyncToyopucDeviceClient):
    def __init__(self) -> None:
        object.__setattr__(self, "_client", _DummyUtilitySyncClient())


class _DummySurfaceSyncClient(_DummyHighLevelClient):
    def __init__(self) -> None:
        super().__init__()
        self.read_dword_map: dict[str, list[int]] = {}
        self.write_dword_calls: list[tuple[str, list[int], bool]] = []

    def resolve_device(self, device: str):
        return super().resolve_device(device)

    def read_dwords(self, device: int | str, count: int, *, atomic_transfer: bool = False):
        assert isinstance(device, str)
        return self.read_dword_map[device][:count]

    def write_dwords(self, device: int | str, values, *, atomic_transfer: bool = False):
        assert isinstance(device, str)
        self.write_dword_calls.append((device, list(values), atomic_transfer))


class _DummyAsyncSurfaceClient(AsyncToyopucDeviceClient):
    def __init__(self) -> None:
        object.__setattr__(self, "_client", _DummySurfaceSyncClient())

    async def _run_sync_in_worker(self, func, /, *args, **kwargs):
        return func(*args, **kwargs)


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
    client.values = {"B0000": (1 << 10) | (1 << 15)}

    async def run_checks() -> None:
        snapshot = await read_named(client, ["B0000.A", "B0000.F"])
        assert snapshot == {"B0000.A": True, "B0000.F": True}

    asyncio.run(run_checks())


def test_normalize_address_uses_profile_rules() -> None:
    assert normalize_address("p1-d0000", profile="TOYOPUC-Plus:Plus Extended mode") == "P1-D0000"


def test_public_device_address_helpers_parse_and_format() -> None:
    typed = parse_device_address("p1-d0100:f", profile="Generic")
    bit = parse_device_address("p1-d0100.a", profile="Generic")

    assert typed.text == "P1-D0100:F"
    assert typed.base_device == "P1-D0100"
    assert typed.dtype == "F"
    assert typed.bit_index is None
    assert bit.text == "P1-D0100.A"
    assert bit.base_device == "P1-D0100"
    assert bit.dtype == "BIT_IN_WORD"
    assert bit.bit_index == 10
    assert format_device_address(typed) == "P1-D0100:F"
    assert format_device_address(bit) == "P1-D0100.A"
    assert format_device_address("p1-d0100:s", profile="Generic") == "P1-D0100:S"


def test_public_device_address_helpers_return_none_on_invalid_input() -> None:
    assert try_parse_device_address("P1-D1000", profile="TOYOPUC-Plus:Plus Standard mode") is None
    assert try_parse_device_address("P1-D0100.10", profile="Generic") is None


def test_connection_options_defaults() -> None:
    options = ToyopucConnectionOptions("127.0.0.1")
    assert options.port == 1025
    assert options.local_port == 0
    assert options.transport == "tcp"
    assert options.timeout == 3.0
    assert options.retries == 0
    assert options.retry_delay == 0.2


def test_open_and_connect_accepts_options(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int, dict[str, object]]] = []

    class _FakeAsyncClient:
        def __init__(self, host: str, port: int, **kwargs: object) -> None:
            calls.append((host, port, kwargs))

        async def connect(self) -> None:
            return None

    monkeypatch.setattr("toyopuc.async_client.AsyncToyopucDeviceClient", _FakeAsyncClient, raising=False)

    async def run() -> None:
        client = await open_and_connect(ToyopucConnectionOptions("127.0.0.1", retries=2))
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
                "recv_bufsize": 8192,
                "trace_hook": None,
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
        assert await read_words_chunked(client, "B0000", 4, max_words_per_request=2) == [1, 2, 3, 4]
        assert await read_dwords_chunked(client, "B0000", 2, max_dwords_per_request=1) == [0x12345678, 0xCAFEBABE]

        await write_words_single_request(client, "B0000", [10, 11])
        await write_dwords_single_request(client, "B0000", [0x12345678])
        await write_words_chunked(client, "B0000", [20, 21, 22], max_words_per_request=2)
        await write_dwords_chunked(client, "B0000", [0x11111111, 0x22222222], max_dwords_per_request=1)

    asyncio.run(run_checks())

    assert client.word_writes == [
        (addr0, [10, 11]),
        (addr0, [20, 21]),
        (addr2, [22]),
    ]
    assert client.write_dword_calls == [
        ("B0000", [0x12345678], True),
        ("B0000", [0x11111111], True),
        ("B0002", [0x22222222], True),
    ]
