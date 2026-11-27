"""Tests für node_base/receiver.py. Ausführen mit: python -m unittest discover tests"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common import protocol as p  # noqa: E402
from node_base.receiver import Receiver, format_event  # noqa: E402

MAC_A = b"\x01\x02\x03\x04\x05\x06"
MAC_B = b"\xaa\xbb\xcc\xdd\xee\xff"


class TestReceiver(unittest.TestCase):
    def setUp(self):
        self.rx = Receiver(names={MAC_A: "Kompression"})

    def test_decodes_compression(self):
        ev = self.rx.handle(MAC_A, p.compression(1, 999, 52.0, 108.0), 5000)
        self.assertEqual(ev.node, "Kompression")
        self.assertEqual(ev.arrival_ms, 5000)
        self.assertEqual(ev.lost, 0)
        self.assertIn("Tiefe  52.0 mm", format_event(ev))

    def test_unknown_mac_shown_as_address(self):
        ev = self.rx.handle(MAC_B, p.ventilation(1, 0, 550, 1000), 0)
        self.assertEqual(ev.node, "aa:bb:cc:dd:ee:ff")
        self.assertIn("Volumen  550 ml", format_event(ev))

    def test_counts_lost_packets(self):
        self.rx.handle(MAC_A, p.heartbeat(10, 0), 0)
        ev = self.rx.handle(MAC_A, p.heartbeat(13, 0), 100)
        self.assertEqual(ev.lost, 2)
        self.assertEqual(self.rx.nodes[MAC_A].lost, 2)
        self.assertIn("2 Paket(e) verloren", format_event(ev))

    def test_seq_wraparound(self):
        self.rx.handle(MAC_A, p.heartbeat(65535, 0), 0)
        self.assertEqual(self.rx.handle(MAC_A, p.heartbeat(0, 0), 10).lost, 0)

    def test_node_restart_not_counted_as_loss(self):
        self.rx.handle(MAC_A, p.heartbeat(5000, 0), 0)
        self.assertEqual(self.rx.handle(MAC_A, p.heartbeat(0, 0), 10).lost, 0)

    def test_duplicate_ignored(self):
        self.rx.handle(MAC_A, p.heartbeat(1, 0), 0)
        self.assertIsNone(self.rx.handle(MAC_A, p.heartbeat(1, 0), 5))
        self.assertEqual(self.rx.duplicates, 1)

    def test_invalid_ignored(self):
        self.assertIsNone(self.rx.handle(MAC_A, b"kaputt", 0))
        self.assertIsNone(self.rx.handle(MAC_A, p.pack(9, 0, 0), 0))
        self.assertEqual(self.rx.invalid, 2)

    def test_timeout_and_comeback(self):
        self.rx.handle(MAC_A, p.heartbeat(1, 0), 1000)
        self.assertEqual(self.rx.check_timeouts(4000), [])
        self.assertEqual(self.rx.check_timeouts(4001), ["Kompression"])
        self.assertEqual(self.rx.check_timeouts(5000), [])  # nur einmal melden
        ev = self.rx.handle(MAC_A, p.heartbeat(2, 0), 6000)
        self.assertTrue(ev.came_back)
        self.assertIn("wieder da", format_event(ev))

    def test_custom_ticks_diff(self):
        rx = Receiver(ticks_diff=lambda a, b: 10_000)
        rx.handle(MAC_A, p.heartbeat(1, 0), 0)
        self.assertEqual(len(rx.check_timeouts(0)), 1)


if __name__ == "__main__":
    unittest.main()
