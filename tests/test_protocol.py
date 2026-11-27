"""Tests für common/protocol.py. Ausführen mit: python -m unittest discover tests"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common import protocol as p  # noqa: E402


class TestProtocol(unittest.TestCase):
    def test_size(self):
        import struct
        self.assertEqual(struct.calcsize(p.FORMAT), p.SIZE)
        self.assertEqual(len(p.heartbeat(0, 0)), 12)

    def test_compression_roundtrip(self):
        pkt = p.unpack(p.compression(7, 123456, 54.3, 110.5, not_released=True))
        self.assertEqual(pkt.typ, p.TYP_COMPRESSION)
        self.assertEqual(pkt.seq, 7)
        self.assertEqual(pkt.t_ms, 123456)
        self.assertEqual(pkt.wert1, 543)
        self.assertEqual(pkt.wert2, 1105)
        self.assertAlmostEqual(p.depth_mm(pkt), 54.3)
        self.assertAlmostEqual(p.rate_per_min(pkt), 110.5)
        self.assertTrue(p.not_released(pkt))

    def test_ventilation_roundtrip(self):
        pkt = p.unpack(p.ventilation(1, 5000, 550, 1020))
        self.assertEqual((pkt.typ, pkt.wert1, pkt.wert2, pkt.flags),
                         (p.TYP_VENTILATION, 550, 1020, 0))

    def test_byte_layout(self):
        raw = p.pack(p.TYP_COMPRESSION, 0x0102, 0x03040506, 0x0708, 0x090A, 0x01)
        self.assertEqual(raw, bytes([1, 0x02, 0x01, 0x06, 0x05, 0x04, 0x03,
                                     0x08, 0x07, 0x0A, 0x09, 0x01]))

    def test_wraparound_and_clamp(self):
        pkt = p.unpack(p.pack(p.TYP_COMPRESSION, 65536 + 5, 2**32 + 9, 70000, -3))
        self.assertEqual((pkt.seq, pkt.t_ms, pkt.wert1, pkt.wert2), (5, 9, 0xFFFF, 0))

    def test_pack_into_reuses_buffer(self):
        buf = bytearray(p.SIZE)
        self.assertIs(p.pack_into(buf, p.TYP_HEARTBEAT, 1, 2), buf)
        self.assertEqual(p.unpack(buf).typ, p.TYP_HEARTBEAT)

    def test_unpack_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            p.unpack(b"\x01" * 11)
        with self.assertRaises(ValueError):
            p.unpack(p.pack(9, 0, 0))

    def test_lost_between(self):
        self.assertEqual(p.lost_between(10, 11), 0)
        self.assertEqual(p.lost_between(10, 14), 3)
        self.assertEqual(p.lost_between(65534, 1), 2)


if __name__ == "__main__":
    unittest.main()
