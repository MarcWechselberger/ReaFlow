"""Hauptschleife des Kompressionsknotens (Hand-Puck, XIAO ESP32-S3).

Stand M1: Testsender ohne Sensoren. Simuliert 30 Kompressionen mit etwa
110/min und wechselnder Tiefe, dann 5 s Pause für die Beatmungen, und
wiederholt das. Jede siebte Kompression ist als nicht entlastet markiert.
Dazu jede Sekunde ein Lebenszeichen.

Auf das Board kopieren (flach, ohne Ordner):
    mpremote cp common/protocol.py common/config.py common/sender.py common/radio.py node_compression/main.py :
"""

import time

import radio
from sender import Sender

RATE_PER_MIN = 110
INTERVAL_MS = 60000 // RATE_PER_MIN  # Abstand zweier Kompressionen
COMPRESSIONS_PER_CYCLE = 30
PAUSE_MS = 5000


def test_depth_mm(n):
    """Tiefe der n-ten Kompression: läuft zwischen 45 und 64 mm hin und her."""
    return 45 + (n * 3) % 20


def main():
    e = radio.setup("Kompression")
    peer = radio.base_peer(e)
    tx = Sender(lambda data: e.send(peer, data), ticks_diff=time.ticks_diff)

    n = 0                    # Kompressionen im aktuellen Zyklus
    total = 0
    next_ms = time.ticks_ms()
    print("Sende Testpakete ...")

    while True:
        now = time.ticks_ms()
        tx.tick(now)

        if time.ticks_diff(now, next_ms) >= 0:
            total += 1
            depth = test_depth_mm(total)
            released = total % 7 != 0
            ok = tx.compression(now, depth, RATE_PER_MIN, not_released=not released)
            print("#%-5d Kompression %2d/%d  %d mm%s%s"
                  % (tx.seq - 1, n + 1, COMPRESSIONS_PER_CYCLE, depth,
                     "" if released else "  nicht entlastet",
                     "" if ok else "  SENDEFEHLER"))
            n += 1
            if n < COMPRESSIONS_PER_CYCLE:
                next_ms = time.ticks_add(next_ms, INTERVAL_MS)
            else:
                n = 0
                next_ms = time.ticks_add(next_ms, PAUSE_MS)
                print("Pause (gesendet %d, Fehler %d)" % (tx.sent, tx.failed))

        time.sleep_ms(5)


main()
