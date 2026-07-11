"""TOYOPUC communication package with high-level helpers as the recommended user surface.

The primary user-facing entry points are:

- ``ToyopucConnectionOptions`` / ``open_and_connect``
- ``read_typed`` / ``write_typed``
- ``read_words_single_request`` / ``read_dwords_single_request``
- ``write_bit_in_word``
- ``read_named`` / ``poll``

Low-level clients and address helpers remain exported for advanced workflows,
but the helpers above are the preferred surface for normal application code
and generated user documentation.
"""

__version__ = "3.1.0"

from .address import (
    encode_bit_address,
    encode_byte_address,
    encode_exno_bit_u32,
    encode_exno_byte_u32,
    encode_ext_no_address,
    encode_fr_word_addr32,
    encode_program_bit_address,
    encode_program_byte_address,
    encode_program_word_address,
    encode_word_address,
    fr_block_ex_no,
    parse_address,
    parse_prefixed_address,
    split_u32_words,
)
from .async_client import AsyncToyopucClient, AsyncToyopucDeviceClient
from .client import ToyopucClient
from .errors import ToyopucError, ToyopucProtocolError, ToyopucTimeoutError
from .high_level import ResolvedDevice, ToyopucDeviceClient, resolve_device
from .profiles import (
    ToyopucAddressRange,
    ToyopucAreaDescriptor,
    ToyopucDeviceCatalog,
    ToyopucDeviceMatrixRow,
    ToyopucPlcProfile,
    ToyopucPlcProfileDescriptor,
    ToyopucPlcProfiles,
    display_name,
    plc_profile_descriptors,
)
from .protocol import ClockData, CpuStatusData
from .relay import RelayLayer, format_relay_hop, normalize_relay_hops, parse_relay_hops
from .utils import (
    ToyopucAddress,
    ToyopucConnectionOptions,
    format_device_address,
    normalize_address,
    open_and_connect,
    parse_device_address,
    poll,
    read_dwords,
    read_dwords_single_request,
    read_named,
    read_typed,
    read_words,
    read_words_single_request,
    try_parse_device_address,
    write_bit_in_word,
    write_dwords_single_request,
    write_typed,
    write_words_single_request,
)

__all__ = [
    "ToyopucClient",
    "AsyncToyopucClient",
    "AsyncToyopucDeviceClient",
    "ToyopucDeviceClient",
    "ResolvedDevice",
    "ClockData",
    "CpuStatusData",
    "RelayLayer",
    "ToyopucError",
    "ToyopucProtocolError",
    "ToyopucTimeoutError",
    "ToyopucConnectionOptions",
    "ToyopucAddress",
    "format_device_address",
    "normalize_address",
    "open_and_connect",
    "parse_device_address",
    "poll",
    "read_dwords",
    "read_dwords_single_request",
    "read_named",
    "read_typed",
    "read_words",
    "read_words_single_request",
    "write_bit_in_word",
    "write_dwords_single_request",
    "write_typed",
    "write_words_single_request",
    "try_parse_device_address",
    "parse_address",
    "parse_prefixed_address",
    "encode_word_address",
    "encode_byte_address",
    "encode_bit_address",
    "encode_program_word_address",
    "encode_program_byte_address",
    "encode_program_bit_address",
    "encode_exno_bit_u32",
    "encode_exno_byte_u32",
    "split_u32_words",
    "encode_ext_no_address",
    "fr_block_ex_no",
    "encode_fr_word_addr32",
    "parse_relay_hops",
    "normalize_relay_hops",
    "format_relay_hop",
    "resolve_device",
    "ToyopucAddressRange",
    "ToyopucAreaDescriptor",
    "ToyopucDeviceCatalog",
    "ToyopucDeviceMatrixRow",
    "ToyopucPlcProfile",
    "ToyopucPlcProfileDescriptor",
    "ToyopucPlcProfiles",
    "display_name",
    "plc_profile_descriptors",
]
