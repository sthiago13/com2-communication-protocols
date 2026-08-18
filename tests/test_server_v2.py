import unittest
from concurrent.futures import ThreadPoolExecutor

from server.protocol_v2 import decode_frame, encode_frame
from server.server_v2 import MessageProcessor


class MessageProcessorTests(unittest.TestCase):
    def test_duplicate_sequence_reuses_ack_without_processing_twice(self):
        processor = MessageProcessor()
        request = encode_frame("MSG", 9, "Pago 100")

        first_response, first_event = processor.handle(request)
        second_response, second_event = processor.handle(request)

        self.assertEqual(first_event, "processed")
        self.assertEqual(second_event, "duplicate")
        self.assertEqual(second_response, first_response)
        self.assertEqual(processor.processed_count, 1)
        self.assertEqual(decode_frame(first_response)["type"], "ACK")

    def test_corrupted_frame_returns_nack_for_same_sequence(self):
        processor = MessageProcessor()
        request = bytearray(encode_frame("MSG", 5, "Hola"))
        request[-1] = ord("A")

        response, event = processor.handle(bytes(request))

        frame = decode_frame(response)
        self.assertEqual(event, "checksum-error")
        self.assertEqual(frame["type"], "NACK")
        self.assertEqual(frame["sequence"], 5)
        self.assertEqual(processor.processed_count, 0)

    def test_same_sequence_with_different_payload_is_rejected(self):
        processor = MessageProcessor()
        processor.handle(encode_frame("MSG", 1, "Hola mundo"))

        response, event = processor.handle(encode_frame("MSG", 1, "Pago 100"))

        frame = decode_frame(response)
        self.assertEqual(event, "sequence-conflict")
        self.assertEqual(frame["type"], "ERROR")
        self.assertEqual(frame["payload"], "SEQUENCE_CONFLICT")
        self.assertEqual(processor.processed_count, 1)

    def test_same_sequence_from_different_clients_is_processed_independently(self):
        processor = MessageProcessor()

        first_response, first_event = processor.handle(
            encode_frame("MSG", 1, "Cliente A"), client_id=("127.0.0.1", 50001)
        )
        second_response, second_event = processor.handle(
            encode_frame("MSG", 1, "Cliente B"), client_id=("127.0.0.1", 50002)
        )

        self.assertEqual(first_event, "processed")
        self.assertEqual(second_event, "processed")
        self.assertEqual(decode_frame(first_response)["payload"], "RECIBIDO: Cliente A")
        self.assertEqual(decode_frame(second_response)["payload"], "RECIBIDO: Cliente B")
        self.assertEqual(processor.processed_count, 2)

    def test_concurrent_duplicates_are_processed_exactly_once(self):
        processor = MessageProcessor()
        request = encode_frame("MSG", 7, "Pago concurrente")
        client = ("127.0.0.1", 50003)

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: processor.handle(request, client), range(20)))

        events = [event for _, event in results]
        self.assertEqual(events.count("processed"), 1)
        self.assertEqual(events.count("duplicate"), 19)
        self.assertEqual(processor.processed_count, 1)


if __name__ == "__main__":
    unittest.main()
