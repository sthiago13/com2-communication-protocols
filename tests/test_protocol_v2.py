import unittest

from server.protocol_v2 import ChecksumError, decode_frame, encode_frame


class ProtocolV2Tests(unittest.TestCase):
    def test_round_trip_preserves_utf8_payload(self):
        raw = encode_frame("MSG", 7, "acción|segura")

        self.assertEqual(
            decode_frame(raw),
            {"version": "V2", "type": "MSG", "sequence": 7, "payload": "acción|segura"},
        )

    def test_rejects_same_length_payload_corruption(self):
        raw = bytearray(encode_frame("MSG", 7, "Hola mundo"))
        raw[-1] = ord("A")

        with self.assertRaises(ChecksumError) as context:
            decode_frame(bytes(raw))

        self.assertEqual(context.exception.sequence, 7)

    def test_supports_ack_and_nack_frames(self):
        for message_type in ("ACK", "NACK"):
            with self.subTest(message_type=message_type):
                self.assertEqual(decode_frame(encode_frame(message_type, 3, "OK"))["type"], message_type)


if __name__ == "__main__":
    unittest.main()
