#!/usr/bin/env python3
"""Robust UDP server with CRC32 checks and duplicate suppression."""

from __future__ import annotations

import argparse
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Hashable

try:
    from .protocol_v2 import ChecksumError, FrameError, decode_frame, encode_frame
except ImportError:  # Direct execution: python server/server_v2.py
    from protocol_v2 import ChecksumError, FrameError, decode_frame, encode_frame


class MessageProcessor:
    """Process each sequence once and cache its ACK for duplicate requests."""

    def __init__(self) -> None:
        self._responses: dict[tuple[Hashable, int], tuple[bytes, bytes]] = {}
        self.processed_count = 0
        self._lock = threading.Lock()

    def handle(self, raw: bytes, client_id: Hashable = "default-client") -> tuple[bytes, str]:
        try:
            frame = decode_frame(raw)
        except ChecksumError as error:
            sequence = error.sequence if error.sequence is not None else 0
            return encode_frame("NACK", sequence, "CRC_MISMATCH"), "checksum-error"
        except FrameError as error:
            sequence = error.sequence if error.sequence is not None else 0
            return encode_frame("ERROR", sequence, str(error)), "malformed"

        sequence = int(frame["sequence"])
        if frame["type"] != "MSG":
            return encode_frame("ERROR", sequence, "EXPECTED_MSG"), "unexpected-type"
        key = (client_id, sequence)
        with self._lock:
            if key in self._responses:
                original_request, cached_response = self._responses[key]
                if raw == original_request:
                    return cached_response, "duplicate"
                return encode_frame("ERROR", sequence, "SEQUENCE_CONFLICT"), "sequence-conflict"

            response = encode_frame("ACK", sequence, f"RECIBIDO: {frame['payload']}")
            self._responses[key] = (raw, response)
            self.processed_count += 1
            return response, "processed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Protocol V2 robust UDP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=9001, type=int)
    parser.add_argument("--workers", default=4, type=int)
    parser.add_argument("--processing-delay-ms", default=0, type=int)
    return parser.parse_args()


def handle_datagram(
    server: socket.socket,
    processor: MessageProcessor,
    raw: bytes,
    client_address: tuple[str, int],
    processing_delay_ms: int,
) -> None:
    worker = threading.current_thread().name
    print(f"[server-v2] START worker={worker} client={client_address}", flush=True)
    if processing_delay_ms > 0:
        time.sleep(processing_delay_ms / 1000)

    response, event = processor.handle(raw, client_address)
    response_frame = decode_frame(response)
    sequence = response_frame["sequence"]
    if event == "processed":
        print(f"[server-v2] processed seq={sequence} payload={response_frame['payload']!r}", flush=True)
    elif event == "duplicate":
        print(f"[server-v2] duplicate seq={sequence}; resent cached ACK without processing", flush=True)
    elif event == "checksum-error":
        print(f"[server-v2] rejected corrupted seq={sequence}; sent NACK", flush=True)
    else:
        print(f"[server-v2] rejected seq={sequence}; event={event} error={response_frame['payload']!r}", flush=True)
    server.sendto(response, client_address)
    print(f"[server-v2] END worker={worker} client={client_address} event={event}", flush=True)


def main() -> None:
    args = parse_args()
    processor = MessageProcessor()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind((args.host, args.port))
        print(
            f"[server-v2] listening on udp://{args.host}:{args.port} "
            f"workers={args.workers} delay_ms={args.processing_delay_ms}"
        )
        with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="udp-worker") as executor:
            while True:
                raw, client_address = server.recvfrom(65_535)
                executor.submit(
                    handle_datagram,
                    server,
                    processor,
                    raw,
                    client_address,
                    args.processing_delay_ms,
                )


if __name__ == "__main__":
    main()
