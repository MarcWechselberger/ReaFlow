"""Tests für common/sender.py. Ausführen mit: python -m unittest discover tests"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common import protocol as p  # noqa: E402
from common.sender import Sender  # noqa: E402
from node_base.receiver import Receiver  # noqa: E402

MAC = b"\x01\x02\x03\x04\x05\x06"


class FakeRadio:
    def __init__(self, result=True):
        self.packets = []
        self.result = result

    def send(self, data):
        self.packets.append(bytes(data))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class TestSender(unittest.TestCase):
    def test_seq_shared_across_types(self):
        radio = FakeRadio()
        tx = Sender(radio.send)
        tx.tick(0)
        tx.compression(10, 50.0, 110)
        tx.ventilation(20, 500, 1000)
        pkts = [p.unpack(d) for d in radio.packets]
        self.assertEqual([k.seq for k in pkts], [0, 1, 2])
        self.assertEqual([k.typ for k in pkts],
                         [p.TYP_HEARTBEAT, p.TYP_COMPRESSION, p.TYP_VENTILATION])
        self.assertEqual(pkts[1].wert1, 500)
        self.assertEqual(pkts[2].wert2, 1000)

    def test_heartbeat_interval(self):
        radio = FakeRadio()
        tx = Sender(radio.send)
        sent = [t for t in range(0, 3500, 100) if tx.tick(t)]
        self.assertEqual(sent, [0, 1000, 2000, 3000])

    def test_seq_wraps(self):
        radio = FakeRadio()
        tx = Sender(radio.send)
        tx.seq = 0xFFFF
        tx.compression(0, 50, 110)
        tx.compression(1, 50, 110)
        self.assertEqual([p.unpack(d).seq for d in radio.packets], [0xFFFF, 0])

    def test_send_failure_counted(self):
        tx = Sender(FakeRadio(result=False).send)
        self.assertFalse(tx.compression(0, 50, 110))
        tx = Sender(FakeRadio(result=OSError("ESP_ERR_ESPNOW_NO_MEM")).send)
        self.assertFalse(tx.ventilation(0, 500, 1000))
        self.assertEqual((tx.sent, tx.failed, tx.seq), (0, 1, 1))

    def test_none_result_counts_as_sent(self):
        tx = Sender(FakeRadio(result=None).send)
        self.assertTrue(tx.tick(0))
        self.assertEqual((tx.sent, tx.failed), (1, 0))

    def test_end_to_end_with_receiver(self):
        radio = FakeRadio()
        tx = Sender(radio.send)
        tx.tick(0)
        tx.compression(500, 55.5, 110, not_released=True)
        tx.compression(1045, 48.0, 110)
        radio.packets.pop()  # ein Paket geht verloren
        tx.tick(1000)

        rx = Receiver(names={MAC: "Kompression"})
        events = [rx.handle(MAC, d, i) for i, d in enumerate(radio.packets)]
        self.assertTrue(all(events))
        self.assertTrue(p.not_released(events[1].packet))
        self.assertAlmostEqual(p.depth_mm(events[1].packet), 55.5)
        self.assertEqual(events[2].lost, 1)
        self.assertEqual(rx.nodes[MAC].lost, 1)


if __name__ == "__main__":
    unittest.main()
