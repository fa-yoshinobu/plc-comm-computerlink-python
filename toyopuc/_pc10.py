from __future__ import annotations

from collections.abc import Sequence

from .client import ToyopucClient
from .errors import ToyopucProtocolError


def _read_pc10_multi_bits(client: ToyopucClient, addrs32: Sequence[int]) -> list[int]:
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
    return bytes(payload)


def _pack_pc10_multi_word_payload(addr32_values: Sequence[tuple[int, int]]) -> bytes:
    payload = bytearray(4 + len(addr32_values) * 4 + len(addr32_values) * 2)
    payload[2] = len(addr32_values) & 0xFF
    for i, (addr32, _) in enumerate(addr32_values):
        payload[4 + i * 4 : 8 + i * 4] = addr32.to_bytes(4, "little")
    values_offset = 4 + len(addr32_values) * 4
    for i, (_, value) in enumerate(addr32_values):
        payload[values_offset + i * 2 : values_offset + i * 2 + 2] = int(value & 0xFFFF).to_bytes(2, "little")
    return bytes(payload)
