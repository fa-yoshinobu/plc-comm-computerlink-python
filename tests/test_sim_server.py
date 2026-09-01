from scripts.sim_server import Memory, handle_command
from toyopuc.protocol import build_command, parse_response


def test_pc10_multi_read_response_echoes_request_counts_before_data() -> None:
    memory = Memory()
    memory.pc10[0x00040000] = 0x1234
    memory.pc10[0x00040200] = 0x5678
    request = build_command(
        0xC4,
        bytes.fromhex("00 00 02 00 00 00 04 00 00 02 04 00"),
    )

    response = parse_response(handle_command(memory, request))

    assert response.data == bytes.fromhex("00 00 02 00 34 12 78 56")


def test_pc10_multi_write_parses_each_interleaved_address_and_value() -> None:
    memory = Memory()
    request = build_command(
        0xC5,
        bytes.fromhex("00 00 02 00 00 00 04 00 34 12 00 02 04 00 78 56"),
    )

    response = parse_response(handle_command(memory, request))

    assert response.rc == 0
    assert memory.pc10 == {0x00040000: 0x1234, 0x00040200: 0x5678}


def test_pc10_multi_write_parses_interleaved_bit_address_and_data_byte() -> None:
    memory = Memory()
    request = build_command(
        0xC5,
        bytes.fromhex("02 00 00 00 00 00 00 04 01 01 00 00 04 00"),
    )

    response = parse_response(handle_command(memory, request))

    assert response.rc == 0
    assert memory.pc10 == {0x04000000: 1, 0x04000001: 0}
