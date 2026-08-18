"""Wire format shared by the V1 server implementation.

Frames are UTF-8 bytes with the format: V1|TYPE|SEQUENCE|LENGTH|PAYLOAD.
LENGTH is the number of UTF-8 bytes in PAYLOAD.
"""

from __future__ import annotations


ALLOWED_TYPES = {"MSG", "RESPONSE", "ERROR"}


class FrameError(ValueError):
    """Raised when a datagram does not match the V1 frame format."""


def encode_frame(message_type: str, sequence: int, payload: str) -> bytes:
    if message_type not in ALLOWED_TYPES:
        raise FrameError(f"unsupported type: {message_type}")
    if not isinstance(sequence, int) or sequence < 0:
        raise FrameError("sequence must be a non-negative integer")

    payload_bytes = payload.encode("utf-8")
    header = f"V1|{message_type}|{sequence}|{len(payload_bytes)}|"
    return header.encode("ascii") + payload_bytes


def decode_frame(raw: bytes) -> dict[str, object]:
    fields = raw.split(b"|", 4)
    if len(fields) != 5:
        raise FrameError("frame must contain five fields")
    header, payload_bytes = fields[:4], fields[4]

    try:
        version, message_type, sequence_text, length_text = [field.decode("ascii") for field in header]
        sequence = int(sequence_text)
        declared_length = int(length_text)
        payload = payload_bytes.decode("utf-8")
    except (UnicodeDecodeError, ValueError) as error:
        raise FrameError("frame header or payload is invalid") from error

    if version != "V1":
        raise FrameError(f"unsupported version: {version}")
    if message_type not in ALLOWED_TYPES:
        raise FrameError(f"unsupported type: {message_type}")
    if sequence < 0 or declared_length < 0:
        raise FrameError("sequence and length must be non-negative")
    if declared_length != len(payload_bytes):
        raise FrameError("declared payload length does not match datagram")

    return {"version": version, "type": message_type, "sequence": sequence, "payload": payload}
