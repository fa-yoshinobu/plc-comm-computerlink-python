from __future__ import annotations

import asyncio

import pytest

from toyopuc import AsyncToyopucDeviceClient, ToyopucClient, ToyopucDeviceClient, ToyopucProtocolError
from toyopuc.protocol import FT_RESPONSE, _parse_response_view, build_word_read, parse_response
from toyopuc.relay import _unwrap_relay_response_chain_view


def _response(command: int, data: bytes = b"", *, rc: int = 0) -> bytes:
    length = 1 + len(data)
    return bytes((FT_RESPONSE, rc, length & 0xFF, length >> 8, command)) + data


def _relay_response(link: int, station: int, command: int, data: bytes) -> bytes:
    inner_length = 1 + len(data)
    inner = bytes((inner_length & 0xFF, inner_length >> 8, command)) + data
    return _response(0x60, bytes((link, station & 0xFF, station >> 8, 0x06)) + inner)


def test_private_response_view_borrows_frame_and_public_response_owns_payload() -> None:
    raw = bytearray(_response(0x1C, b"\x34\x12"))
    view = _parse_response_view(memoryview(raw))
    owned = view.to_owned()
    public = parse_response(memoryview(raw))

    raw[5] = 0x78

    assert view.data[0] == 0x78
    assert owned.data == b"\x34\x12"
    assert public.data == b"\x34\x12"


def test_relay_view_unwraps_inner_payload_without_copy() -> None:
    final = _response(0x1C, b"\x34\x12")
    inner = _response(0x60, bytes((0x34, 0x03, 0x00, 0x06)) + final[2:])
    raw = bytearray(_response(0x60, bytes((0x12, 0x02, 0x00, 0x06)) + inner[2:]))

    layers, response = _unwrap_relay_response_chain_view(_parse_response_view(memoryview(raw)))

    assert [(layer.link_no, layer.station_no) for layer in layers] == [(0x12, 2), (0x34, 3)]
    assert response is not None
    raw[-1] = 0x56
    assert response.data[1] == 0x56


def test_prepared_relay_rejects_wrong_response_route() -> None:
    client = ToyopucClient("127.0.0.1", 1025, transport="tcp")
    prepared = client._prepare_relay_read("P1-L2:N2", build_word_read(0, 1))

    class Script:
        @staticmethod
        def exchange(_payload: bytes, _state_changing: bool) -> bytes:
            return _relay_response(0x13, 2, 0x1C, b"\x34\x12")

    client._async_transport_script = Script()
    with pytest.raises(ToyopucProtocolError, match="Unexpected relay response route"):
        client._send_prepared_relay_read_decoded(prepared, lambda response: response.data)


def test_async_aggregate_encodes_each_segment_once(monkeypatch: pytest.MonkeyPatch) -> None:
    encoded: list[tuple[str, ...]] = []
    decoded: list[int] = []
    exchanged: list[bytes] = []
    original = ToyopucDeviceClient._build_read_batch_payload
    original_decode = ToyopucDeviceClient._decode_prepared_read_segment

    def counted(devices: list[object]) -> bytes:
        encoded.append(tuple(device.text for device in devices))  # type: ignore[attr-defined]
        return original(devices)  # type: ignore[arg-type]

    monkeypatch.setattr(ToyopucDeviceClient, "_build_read_batch_payload", staticmethod(counted))

    def counted_decode(response: object, segment: object, results: list[object]) -> None:
        decoded.append(segment.result_offset)  # type: ignore[attr-defined]
        original_decode(response, segment, results)  # type: ignore[arg-type]

    monkeypatch.setattr(ToyopucDeviceClient, "_decode_prepared_read_segment", staticmethod(counted_decode))

    async def run() -> list[object]:
        client = AsyncToyopucDeviceClient("127.0.0.1", 1025, transport="tcp", plc_profile="toyopuc:generic")

        async def exchange(payload: bytes, *_args: object) -> bytes:
            exchanged.append(payload)
            count = payload[7] | (payload[8] << 8)
            return _response(payload[4], b"\x00\x00" * count)

        client._exchange = exchange  # type: ignore[method-assign]
        return await client.read("B0000", 513)

    result = asyncio.run(run())
    assert len(result) == 513
    assert len(encoded) == 2
    assert decoded == [0, 512]
    assert len(exchanged) == 2


def test_async_aggregate_finishes_all_preflight_before_first_exchange(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builds = 0
    original = ToyopucDeviceClient._build_read_batch_payload

    def fail_second(devices: list[object]) -> bytes:
        nonlocal builds
        builds += 1
        if builds == 2:
            raise ValueError("synthetic second segment failure")
        return original(devices)  # type: ignore[arg-type]

    monkeypatch.setattr(ToyopucDeviceClient, "_build_read_batch_payload", staticmethod(fail_second))

    async def run() -> None:
        client = AsyncToyopucDeviceClient("127.0.0.1", 1025, transport="tcp", plc_profile="toyopuc:generic")

        async def exchange(*_args: object) -> bytes:
            raise AssertionError("transport must not run before all preflight succeeds")

        client._exchange = exchange  # type: ignore[method-assign]
        with pytest.raises(ValueError, match="second segment failure"):
            await client.read("B0000", 513)

    asyncio.run(run())
    assert builds == 2


def test_async_transport_has_no_client_owned_worker_surface() -> None:
    client = AsyncToyopucDeviceClient("127.0.0.1", 1025, transport="tcp", plc_profile="toyopuc:generic")
    assert not hasattr(client, "_run_sync_in_worker")
    assert not hasattr(client, "_executor")
