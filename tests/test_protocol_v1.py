import unittest

from server.protocol_v1 import FrameError, decode_frame, encode_frame


class ProtocolV1Tests(unittest.TestCase):
    def test_round_trip_preserves_payload_and_sequence(self):
        raw = encode_frame("MSG", 7, "hola|servidor")

        self.assertEqual(
            decode_frame(raw),
            {"version": "V1", "type": "MSG", "sequence": 7, "payload": "hola|servidor"},
        )

    def test_rejects_payload_with_invalid_declared_length(self):
        with self.assertRaises(FrameError):
            decode_frame(b"V1|MSG|7|99|hola")

    def test_rejects_unknown_message_type(self):
        with self.assertRaises(FrameError):
            decode_frame(b"V1|UNKNOWN|7|0|")


if __name__ == "__main__":
    unittest.main()
