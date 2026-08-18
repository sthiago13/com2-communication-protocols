#!/usr/bin/env python3
"""UDP proxy that deterministically injects client-to-server failures.

This is intentionally simple so the first adversarial experiments are reproducible.
"""

from __future__ import annotations

import argparse
import socket


def corrupt_payload_byte(raw: bytes) -> bytes:
    """Change one ASCII letter in the payload without breaking its UTF-8 length.

    V1 has no integrity field, so a same-length valid payload lets the server
    accept altered data instead of rejecting a malformed datagram.
    """
    separator_target = 5 if raw.startswith(b"V2|") else 4
    separators: list[int] = []
    for index, value in enumerate(raw):
        if value == ord("|"):
            separators.append(index)
            if len(separators) == separator_target:
                break
    if len(separators) != separator_target or separators[-1] == len(raw) - 1:
        raise ValueError("frame has no payload byte that can be corrupted")

    corrupted = bytearray(raw)
    for index in range(separators[-1] + 1, len(corrupted)):
        value = corrupted[index]
        if ord("a") <= value <= ord("z"):
            corrupted[index] = value - (ord("a") - ord("A"))
            return bytes(corrupted)
        if ord("A") <= value <= ord("Z"):
            corrupted[index] = value + (ord("a") - ord("A"))
            return bytes(corrupted)
    raise ValueError("payload has no ASCII letter that can be corrupted safely")


def duplicate_datagram(raw: bytes) -> tuple[bytes, bytes]:
    """Return the original datagram and an independent identical copy."""
    return raw, bytes(bytearray(raw))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Protocol V1 adversarial UDP proxy")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--listen-port", default=9000, type=int)
    parser.add_argument("--server-host", default="127.0.0.1")
    parser.add_argument("--server-port", default=9001, type=int)
    parser.add_argument("--drop-client-to-server", default=0, type=int, help="number of first client datagrams to drop")
    parser.add_argument("--corrupt-client-to-server", default=0, type=int, help="number of first client datagrams to corrupt")
    parser.add_argument("--duplicate-client-to-server", default=0, type=int, help="number of first client datagrams to duplicate")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    remaining_drops = args.drop_client_to_server
    remaining_corruptions = args.corrupt_client_to_server
    remaining_duplications = args.duplicate_client_to_server
    client_address: tuple[str, int] | None = None
    server_address = (args.server_host, args.server_port)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as proxy:
        proxy.bind((args.host, args.listen_port))
        print(f"[proxy] listening on udp://{args.host}:{args.listen_port}; forwarding to {server_address}")
        print(f"[proxy] configured client-to-server drops: {remaining_drops}")
        print(f"[proxy] configured client-to-server corruptions: {remaining_corruptions}")
        print(f"[proxy] configured client-to-server duplications: {remaining_duplications}")
        while True:
            raw, sender = proxy.recvfrom(65_535)
            if sender == server_address:
                if client_address is None:
                    print("[proxy] ignored server response because no client is known")
                    continue
                proxy.sendto(raw, client_address)
                print(f"[proxy] forwarded server response to {client_address}")
                continue

            client_address = sender
            if remaining_drops > 0:
                remaining_drops -= 1
                print(f"[proxy] DROPPED client datagram from {sender}; remaining drops: {remaining_drops}")
                continue
            if remaining_corruptions > 0:
                remaining_corruptions -= 1
                try:
                    raw = corrupt_payload_byte(raw)
                except ValueError as error:
                    print(f"[proxy] could not corrupt client datagram from {sender}: {error}")
                else:
                    print(f"[proxy] CORRUPTED client datagram from {sender}; remaining corruptions: {remaining_corruptions}")
            if remaining_duplications > 0:
                remaining_duplications -= 1
                first_copy, second_copy = duplicate_datagram(raw)
                proxy.sendto(first_copy, server_address)
                proxy.sendto(second_copy, server_address)
                print(f"[proxy] DUPLICATED client datagram from {sender}; remaining duplications: {remaining_duplications}")
                continue
            proxy.sendto(raw, server_address)
            print(f"[proxy] forwarded client datagram from {sender} to {server_address}")


if __name__ == "__main__":
    main()
