import unittest

from adversary.drop_proxy import corrupt_payload_byte, duplicate_datagram


class AdversaryTests(unittest.TestCase):
    def test_corruption_changes_payload_without_changing_frame_length(self):
        original = b"V1|MSG|1|5|Hola!"

        corrupted = corrupt_payload_byte(original)

        self.assertNotEqual(corrupted, original)
        self.assertEqual(len(corrupted), len(original))
        self.assertEqual(corrupted[:11], b"V1|MSG|1|5|")
        self.assertNotEqual(corrupted[11:], b"Hola!")

    def test_corruption_rejects_frames_without_a_payload(self):
        with self.assertRaises(ValueError):
            corrupt_payload_byte(b"V1|MSG|1|0|")

    def test_corruption_targets_v2_payload_instead_of_crc_field(self):
        original = b"V2|MSG|1|4|DEADBEEF|Hola"
        prefix = b"V2|MSG|1|4|DEADBEEF|"

        corrupted = corrupt_payload_byte(original)

        self.assertEqual(corrupted[: len(prefix)], prefix)
        self.assertEqual(corrupted[len(prefix) :], b"hola")

    def test_duplication_creates_two_identical_datagrams(self):
        original = b"V1|MSG|1|4|Hola"

        copies = duplicate_datagram(original)

        self.assertEqual(copies, (original, original))
        self.assertIsNot(copies[0], copies[1])


if __name__ == "__main__":
    unittest.main()
