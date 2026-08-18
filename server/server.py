#!/usr/bin/env python3
"""UDP echo server for the initial, intentionally non-resilient protocol."""

from __future__ import annotations

import argparse
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from protocol_v1 import FrameError, decode_frame, encode_frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Protocol V1 UDP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=9001, type=int)
    parser.add_argument("--workers", default=4, type=int)
    parser.add_argument("--processing-delay-ms", default=0, type=int)
    return parser.parse_args()


def handle_datagram(
    server: socket.socket,
    raw: bytes,
    client_address: tuple[str, int],
    processing_delay_ms: int,
) -> None:
    worker = threading.current_thread().name
    print(f"[server] START worker={worker} client={client_address}", flush=True)
    if processing_delay_ms > 0:
        time.sleep(processing_delay_ms / 1000)

    try:
        frame = decode_frame(raw)
    except FrameError as error:
        print(f"[server] discarded malformed frame from {client_address}: {error}", flush=True)
        print(f"[server] END worker={worker} client={client_address} event=malformed", flush=True)
        return

    if frame["type"] != "MSG":
        print(f"[server] ignored non-MSG frame from {client_address}", flush=True)
        print(f"[server] END worker={worker} client={client_address} event=ignored", flush=True)
        return

    print(f"[server] received seq={frame['sequence']} payload={frame['payload']!r}", flush=True)
    response = encode_frame("RESPONSE", int(frame["sequence"]), f"RECIBIDO: {frame['payload']}")
    server.sendto(response, client_address)
    print(f"[server] END worker={worker} client={client_address} event=processed", flush=True)


def main() -> None:
    args = parse_args()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind((args.host, args.port))
        print(
            f"[server] listening on udp://{args.host}:{args.port} "
            f"workers={args.workers} delay_ms={args.processing_delay_ms}"
        )
        with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="udp-worker") as executor:
            while True:
                raw, client_address = server.recvfrom(65_535)
                executor.submit(
                    handle_datagram,
                    server,
                    raw,
                    client_address,
                    args.processing_delay_ms,
                )


if __name__ == "__main__":
    main()
