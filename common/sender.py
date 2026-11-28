"""Senden der Funkpakete in einem Sensorknoten.

Reine Logik ohne machine-, network- oder espnow-Importe: läuft unverändert
am PC und lässt sich dort testen. Die eigentliche Sendefunktion (z. B.
ESPNow.send) wird von außen übergeben.

Ein Knoten hat genau einen seq-Zähler für alle Pakettypen, denn die
Basisstation erkennt verlorene Pakete an Lücken in seq pro Absender.
"""

try:
    import protocol  # auf dem ESP32 liegen alle Dateien flach im Dateisystem
except ImportError:
    from common import protocol


def _default_diff(a, b):
    return a - b


class Sender:
    """Verpackt Messwerte, zählt seq hoch und schickt jede Sekunde ein Lebenszeichen.

    send:         Funktion send(data) -> bool; False oder eine Ausnahme
                  zählen als Sendefehler (der Knoten läuft weiter)
    ticks_diff:   auf dem ESP32 time.ticks_diff übergeben
    heartbeat_ms: Abstand der Lebenszeichen
    """

    def __init__(self, send, ticks_diff=None,
                 heartbeat_ms=protocol.HEARTBEAT_INTERVAL_MS):
        self._send = send
        self.diff = ticks_diff or _default_diff
        self.heartbeat_ms = heartbeat_ms
        self.seq = 0
        self.sent = 0
        self.failed = 0
        self._last_heartbeat_ms = None

    def _transmit(self, data):
        self.seq = (self.seq + 1) & 0xFFFF
        try:
            ok = self._send(data)
        except OSError:
            ok = False
        if ok is False:
            self.failed += 1
        else:
            self.sent += 1
        return ok is not False

    def compression(self, now_ms, depth_mm, rate_per_min, not_released=False):
        """Eine erkannte Kompression senden. Gibt True bei Erfolg zurück."""
        return self._transmit(protocol.compression(
            self.seq, now_ms, depth_mm, rate_per_min, not_released))

    def ventilation(self, now_ms, volume_ml, duration_ms):
        """Eine erkannte Beatmung senden. Gibt True bei Erfolg zurück."""
        return self._transmit(protocol.ventilation(
            self.seq, now_ms, volume_ml, duration_ms))

    def tick(self, now_ms):
        """In der Hauptschleife oft aufrufen; sendet fällige Lebenszeichen.

        Gibt True zurück, wenn gerade ein Lebenszeichen gesendet wurde.
        """
        if (self._last_heartbeat_ms is not None
                and self.diff(now_ms, self._last_heartbeat_ms) < self.heartbeat_ms):
            return False
        self._last_heartbeat_ms = now_ms
        self._transmit(protocol.heartbeat(self.seq, now_ms))
        return True
