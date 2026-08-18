"""Robust V2 frame codec with CRC32 integrity verification."""

from __future__ import annotations

import binascii


ALLOWED_TYPES = {"MSG", "ACK", "NACK", "ERROR"}


class FrameError(ValueError):
    """Raised when a datagram does not match the V2 frame format."""

    def __init__(self, message: str, sequence: int | None = None) -> None:
        super().__init__(message)
        self.sequence = sequence


class ChecksumError(FrameError):
    """Raised when the payload CRC32 does not match the header."""


def _crc32(payload: bytes) -> str:
    return f"{binascii.crc32(payload) & 0xFFFFFFFF:08X}"


def encode_frame(message_type: str, sequence: int, payload: str) -> bytes:
    if message_type not in ALLOWED_TYPES:
        raise FrameError(f"unsupported type: {message_type}", sequence)
    if not isinstance(sequence, int) or sequence < 0:
        raise FrameError("sequence must be a non-negative integer")

    payload_bytes = payload.encode("utf-8")
    header = f"V2|{message_type}|{sequence}|{len(payload_bytes)}|{_crc32(payload_bytes)}|"
    return header.encode("ascii") + payload_bytes


def decode_frame(raw: bytes) -> dict[str, object]:
    fields = raw.split(b"|", 5)
    if len(fields) != 6:
        raise FrameError("frame must contain six fields")

    version_raw, type_raw, sequence_raw, length_raw, crc_raw, payload_bytes = fields
    sequence: int | None = None
    try:
        version = version_raw.decode("ascii")
        message_type = type_raw.decode("ascii")
        sequence = int(sequence_raw.decode("ascii"))
        declared_length = int(length_raw.decode("ascii"))
        declared_crc = crc_raw.decode("ascii").upper()
    except (UnicodeDecodeError, ValueError) as error:
        raise FrameError("frame header is invalid", sequence) from error

    if version != "V2":
        raise FrameError(f"unsupported version: {version}", sequence)
    if message_type not in ALLOWED_TYPES:
        raise FrameError(f"unsupported type: {message_type}", sequence)
    if sequence < 0 or declared_length < 0:
        raise FrameError("sequence and length must be non-negative", sequence)
    if len(declared_crc) != 8 or any(char not in "0123456789ABCDEF" for char in declared_crc):
        raise FrameError("CRC32 must contain eight hexadecimal characters", sequence)
    if declared_length != len(payload_bytes):
        raise FrameError("declared payload length does not match datagram", sequence)
    if declared_crc != _crc32(payload_bytes):
        raise ChecksumError("payload CRC32 mismatch", sequence)

    try:
        payload = payload_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise FrameError("payload is not valid UTF-8", sequence) from error

    return {"version": version, "type": message_type, "sequence": sequence, "payload": payload}
