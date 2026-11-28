"""Hauptschleife des Beatmungsknotens (Flow-Adapter, ESP32-DevKit).

Stand M1: Testsender ohne Sensor. Simuliert alle 21 s zwei Beatmungen im
Abstand von 2,5 s mit wechselndem Volumen und etwa 1 s Insufflationsdauer.
Dazu jede Sekunde ein Lebenszeichen.

Auf das Board kopieren (flach, ohne Ordner):
    mpremote cp common/protocol.py common/config.py common/sender.py common/radio.py node_ventilation/main.py :
"""

import time

import radio
from sender import Sender

BREATHS_PER_PAUSE = 2
BREATH_GAP_MS = 2500
CYCLE_MS = 21000  # ungefähr 30 Kompressionen mit 110/min plus Pause


def test_breath(n):
    """Volumen (ml) und Dauer (ms) der n-ten Beatmung."""
    return 400 + (n * 70) % 300, 900 + (n * 40) % 300


def main():
    e = radio.setup("Beatmung")
    peer = radio.base_peer(e)
    tx = Sender(lambda data: e.send(peer, data), ticks_diff=time.ticks_diff)

    n = 0                    # Beatmungen in der aktuellen Pause
    total = 0
    next_ms = time.ticks_ms()
    print("Sende Testpakete ...")

    while True:
        now = time.ticks_ms()
        tx.tick(now)

        if time.ticks_diff(now, next_ms) >= 0:
            total += 1
            volume, duration = test_breath(total)
            ok = tx.ventilation(now, volume, duration)
            print("#%-5d Beatmung %d/%d  %d ml  %d ms%s"
                  % (tx.seq - 1, n + 1, BREATHS_PER_PAUSE, volume, duration,
                     "" if ok else "  SENDEFEHLER"))
            n += 1
            if n < BREATHS_PER_PAUSE:
                next_ms = time.ticks_add(next_ms, BREATH_GAP_MS)
            else:
                n = 0
                next_ms = time.ticks_add(
                    next_ms, CYCLE_MS - (BREATHS_PER_PAUSE - 1) * BREATH_GAP_MS)
                print("Warte (gesendet %d, Fehler %d)" % (tx.sent, tx.failed))

        time.sleep_ms(5)


main()
