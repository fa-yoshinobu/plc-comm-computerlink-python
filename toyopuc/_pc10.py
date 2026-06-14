from __future__ import annotations

from collections.abc import Sequence

from .client import ToyopucClient
from .errors import ToyopucProtocolError

_PC10_MULTI_READ_MAX_POINTS = 0x7F
_PC10_MULTI_WRITE_MAX_PAYLOAD_BYTES = 0x0200


def _require_pc10_multi_read_count(count: int) -> None:
    if count < 1 or count > _PC10_MULTI_READ_MAX_POINTS:
        raise ValueError(
            f"CMD=C4 PC10 multi-read point count must be 1..0x{_PC10_MULTI_READ_MAX_POINTS:X} "
            f"({_PC10_MULTI_READ_MAX_POINTS})"
        )


def _require_pc10_multi_write_payload(payload: bytes | bytearray) -> None:
    if len(payload) < 1 or len(payload) > _PC10_MULTI_WRITE_MAX_PAYLOAD_BYTES:
        raise ValueError(
            f"CMD=C5 PC10 multi-write payload must be 1..0x{_PC10_MULTI_WRITE_MAX_PAYLOAD_BYTES:X} "
            f"({_PC10_MULTI_WRITE_MAX_PAYLOAD_BYTES}) bytes"
        )


def _read_pc10_multi_bits(client: ToyopucClient, addrs32: Sequence[int]) -> list[int]:
    _require_pc10_multi_read_count(len(addrs32))
    payload = bytearray([len(addrs32) & 0xFF, 0x00, 0x00, 0x00])
    for addr32 in addrs32:
        payload.extend(addr32.to_bytes(4, "little"))
    data = client.pc10_multi_read(bytes(payload))[4:]
    return [(data[i // 8] >> (i % 8)) & 0x01 for i in range(len(addrs32))]


def _parse_ext_multi_bit_data(data: bytes, count: int) -> list[int]:
    need = (count + 7) // 8
    if len(data) < need:
        raise ToyopucProtocolError("Extended multi-bit response too short")
    return [(data[i // 8] >> (i % 8)) & 0x01 for i in range(count)]


def _build_pc10_multi_word_read_payload(addrs32: Sequence[int]) -> bytes:
    _require_pc10_multi_read_count(len(addrs32))
    payload = bytearray(4 + len(addrs32) * 4)
    payload[2] = len(addrs32) & 0xFF
    for i, addr32 in enumerate(addrs32):
        payload[4 + i * 4 : 8 + i * 4] = addr32.to_bytes(4, "little")
    return bytes(payload)


def _parse_pc10_multi_word_data(data: bytes, count: int) -> list[int]:
    need = 4 + count * 2
    if len(data) < need:
        raise ToyopucProtocolError("PC10 multi-word response too short")
    return [int.from_bytes(data[4 + i * 2 : 6 + i * 2], "little") for i in range(count)]


def _read_pc10_multi_words(client: ToyopucClient, addrs32: Sequence[int]) -> list[int]:
    data = client.pc10_multi_read(_build_pc10_multi_word_read_payload(addrs32))
    return _parse_pc10_multi_word_data(data, len(addrs32))


def _read_pc10_block_word(client: ToyopucClient, addr32: int) -> int:
    data = client.pc10_block_read(addr32, 2)
    return int.from_bytes(data[:2], "little")


def _write_pc10_block_word(client: ToyopucClient, addr32: int, value: int) -> None:
    client.pc10_block_write(addr32, int(value & 0xFFFF).to_bytes(2, "little"))


def _pack_pc10_multi_bit_payload(addr32_values: Sequence[tuple[int, int]]) -> bytes:
    payload = bytearray([len(addr32_values) & 0xFF, 0x00, 0x00, 0x00])
    for addr32, _ in addr32_values:
        payload.extend(addr32.to_bytes(4, "little"))
    bit_bytes = bytearray((len(addr32_values) + 7) // 8)
    for i, (_, value) in enumerate(addr32_values):
        if int(value) & 0x01:
            bit_bytes[i // 8] |= 1 << (i % 8)
    payload.extend(bit_bytes)
    _require_pc10_multi_write_payload(payload)
    return bytes(payload)


def _pack_pc10_multi_word_payload(addr32_values: Sequence[tuple[int, int]]) -> bytes:
    payload = bytearray(4 + len(addr32_values) * 4 + len(addr32_values) * 2)
    payload[2] = len(addr32_values) & 0xFF
    for i, (addr32, _) in enumerate(addr32_values):
        payload[4 + i * 4 : 8 + i * 4] = addr32.to_bytes(4, "little")
    values_offset = 4 + len(addr32_values) * 4
    for i, (_, value) in enumerate(addr32_values):
        payload[values_offset + i * 2 : values_offset + i * 2 + 2] = int(value & 0xFFFF).to_bytes(2, "little")
    _require_pc10_multi_write_payload(payload)
    return bytes(payload)
