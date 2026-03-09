"""Public package entry points for `toyopuc`.

Use:
- `ToyopucClient` for low-level protocol-oriented access
- `ToyopucHighLevelClient` for string-address based access
- `resolve_device()` when you want address-family resolution without I/O
"""

from .client import ToyopucClient
from .exceptions import ToyopucError, ToyopucProtocolError, ToyopucTimeoutError
from .address import (
    parse_address,
    parse_prefixed_address,
    encode_word_address,
    encode_byte_address,
    encode_bit_address,
    encode_program_word_address,
    encode_program_byte_address,
    encode_program_bit_address,
    encode_exno_bit_u32,
    encode_exno_byte_u32,
    split_u32_words,
    encode_ext_no_address,
    fr_block_ex_no,
    encode_fr_word_addr32,
)
from .high_level import ResolvedDevice, ToyopucHighLevelClient, resolve_device
from .protocol import ClockData, CpuStatusData

__all__ = [
    'ToyopucClient',
    'ToyopucHighLevelClient',
    'ResolvedDevice',
    'ClockData',
    'CpuStatusData',
    'ToyopucError',
    'ToyopucProtocolError',
    'ToyopucTimeoutError',
    'parse_address',
    'parse_prefixed_address',
    'encode_word_address',
    'encode_byte_address',
    'encode_bit_address',
    'encode_program_word_address',
    'encode_program_byte_address',
    'encode_program_bit_address',
    'encode_exno_bit_u32',
    'encode_exno_byte_u32',
    'split_u32_words',
    'encode_ext_no_address',
    'fr_block_ex_no',
    'encode_fr_word_addr32',
    'resolve_device',
]
