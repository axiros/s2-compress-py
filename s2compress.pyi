"""S2 block compression, compatible with Go klauspost/compress/s2 Encode/Decode."""

__version__: str
DEFAULT_MAX: int
"""Default max_size of decompress: 64 MiB."""
MAX_COMPRESS: int
"""Largest input of compress: 16 MiB (minlz 1.2.3 writes broken blocks above about 16.06 MiB)."""

class S2Error(ValueError):
    """Not an S2 block, or larger than allowed."""

def compress(data: bytes) -> bytes:
    """The S2 block of data. Data larger than MAX_COMPRESS is refused with S2Error: send it
    uncompressed. The GIL is released while it compresses."""

def decompress(data: bytes, max_size: int = ...) -> bytes:
    """The bytes of an S2 block. A block that says it is larger than max_size is refused with
    S2Error before it is decoded. The GIL is released while it decompresses."""

def decoded_len(data: bytes) -> int:
    """The size an S2 block decompresses to, from its header."""
