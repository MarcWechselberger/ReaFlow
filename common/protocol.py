"""Paketformat für alle Funkpakete zwischen den Knoten (ESP-NOW).

Jedes Paket ist 12 Byte lang, little-endian, Format '<BHIHHB':

    Feld   Typ  Inhalt
    typ    B    1 = Kompression, 2 = Beatmung, 3 = Lebenszeichen
    seq    H    laufende Nummer pro Knoten (läuft bei 65535 auf 0 über)
    t_ms   I    Zeit des Knotens in Millisekunden (time.ticks_ms())
    wert1  H    Tiefe in 0,1 mm  bzw.  Volumen in ml
    wert2  H    Frequenz in 0,1/min  bzw.  Insufflationsdauer in ms
    flags  B    Bit 0: nicht vollständig entlastet

Den Absender eines Pakets erkennt die Basisstation an der MAC-Adresse,
nicht am Paketinhalt.

Läuft unverändert unter MicroPython und CPython (keine machine-Importe).
"""

import struct

try:
    from collections import namedtuple
except ImportError:  # ältere MicroPython-Builds
    from ucollections import namedtuple

FORMAT = "<BHIHHB"
SIZE = 12  # == struct.calcsize(FORMAT)

# Pakettypen
TYP_COMPRESSION = 1
TYP_VENTILATION = 2
TYP_HEARTBEAT = 3
TYPES = (TYP_COMPRESSION, TYP_VENTILATION, TYP_HEARTBEAT)

# Knoten-IDs
NODE_COMPRESSION = 1
NODE_VENTILATION = 2
NODE_BASE = 3

# Flags
FLAG_NOT_RELEASED = 0x01  # Bit 0: nicht vollständig entlastet

# Sendeintervall und Ausfallgrenze für Lebenszeichen
HEARTBEAT_INTERVAL_MS = 1000
HEARTBEAT_TIMEOUT_MS = 3000

Packet = namedtuple("Packet", ("typ", "seq", "t_ms", "wert1", "wert2", "flags"))


def _u16(x):
    """Auf den Wertebereich 0..65535 begrenzen (Messwerte, kein Überlauf)."""
    x = int(x)
    if x < 0:
        return 0
    if x > 0xFFFF:
        return 0xFFFF
    return x


def pack_into(buf, typ, seq, t_ms, wert1=0, wert2=0, flags=0):
    """Paket in einen vorab angelegten bytearray(SIZE) schreiben.

    Für die Messschleife gedacht: es wird nichts neu alloziert.
    seq und t_ms laufen über, wert1 und wert2 werden begrenzt.
    """
    struct.pack_into(
        FORMAT, buf, 0,
        typ, seq & 0xFFFF, t_ms & 0xFFFFFFFF,
        _u16(wert1), _u16(wert2), flags & 0xFF,
    )
    return buf


def pack(typ, seq, t_ms, wert1=0, wert2=0, flags=0):
    """Paket als neues bytes-Objekt erzeugen."""
    return bytes(pack_into(bytearray(SIZE), typ, seq, t_ms, wert1, wert2, flags))


def compression(seq, t_ms, depth_mm, rate_per_min, not_released=False):
    """Kompressionspaket. Tiefe in mm, Frequenz pro Minute (Fließkomma erlaubt)."""
    return pack(
        TYP_COMPRESSION, seq, t_ms,
        round(depth_mm * 10), round(rate_per_min * 10),
        FLAG_NOT_RELEASED if not_released else 0,
    )


def ventilation(seq, t_ms, volume_ml, duration_ms):
    """Beatmungspaket. Volumen in ml, Insufflationsdauer in ms."""
    return pack(TYP_VENTILATION, seq, t_ms, round(volume_ml), round(duration_ms))


def heartbeat(seq, t_ms):
    """Lebenszeichen, einmal pro Sekunde von jedem Sensorknoten."""
    return pack(TYP_HEARTBEAT, seq, t_ms)


def unpack(data):
    """Empfangene Bytes in ein Packet zerlegen.

    Wirft ValueError bei falscher Länge oder unbekanntem Typ.
    """
    if len(data) != SIZE:
        raise ValueError("Paketlänge %d statt %d" % (len(data), SIZE))
    p = Packet(*struct.unpack(FORMAT, data))
    if p.typ not in TYPES:
        raise ValueError("unbekannter Pakettyp %d" % p.typ)
    return p


def depth_mm(p):
    """Tiefe eines Kompressionspakets in mm."""
    return p.wert1 / 10


def rate_per_min(p):
    """Frequenz eines Kompressionspakets pro Minute."""
    return p.wert2 / 10


def not_released(p):
    """True, wenn die Kompression nicht vollständig entlastet wurde."""
    return bool(p.flags & FLAG_NOT_RELEASED)


def lost_between(prev_seq, seq):
    """Anzahl verlorener Pakete zwischen zwei aufeinanderfolgenden seq-Werten.

    Berücksichtigt den Überlauf bei 65535. Doppelte oder ältere Pakete ergeben
    einen großen Wert; die Basisstation sollte sie über seq == prev_seq erkennen.
    """
    return (seq - prev_seq - 1) & 0xFFFF
