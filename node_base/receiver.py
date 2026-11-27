"""Empfang und Decodierung der Funkpakete in der Basisstation.

Reine Logik ohne machine-, network- oder espnow-Importe: läuft unverändert
am PC und lässt sich dort testen. Den Funkempfang selbst macht main.py.

Die Basisstation stempelt jedes Paket bei Ankunft mit ihrer eigenen Uhr
(now_ms). Die Uhren der Sensorknoten müssen nicht synchron laufen.
"""

try:
    import protocol  # auf dem ESP32 liegen alle Dateien flach im Dateisystem
except ImportError:
    from common import protocol

# Springt seq um mehr als das zurück oder nach vorn, wurde der Knoten
# vermutlich neu gestartet. Dann zählen wir keine verlorenen Pakete.
RESTART_GAP = 1000


def mac_str(mac):
    return ":".join("%02x" % b for b in mac)


def _default_diff(a, b):
    return a - b


class NodeState:
    """Was die Basisstation über einen Sensorknoten weiß."""

    def __init__(self, name):
        self.name = name
        self.last_seq = None
        self.last_seen_ms = None
        self.online = False
        self.received = 0
        self.lost = 0


class Event:
    """Ein gültig empfangenes Paket samt Ankunftszeit und Verlustinfo."""

    def __init__(self, node, packet, arrival_ms, lost, came_back):
        self.node = node              # Name des Knotens
        self.packet = packet          # protocol.Packet
        self.arrival_ms = arrival_ms  # Uhr der Basisstation
        self.lost = lost              # verlorene Pakete direkt davor
        self.came_back = came_back    # True, wenn der Knoten als ausgefallen galt


class Receiver:
    """Nimmt rohe ESP-NOW-Nachrichten entgegen und verfolgt den Knotenzustand.

    names:      {mac_bytes: "Name"} für bekannte Knoten
    timeout_ms: ohne Paket so lange -> Knoten gilt als ausgefallen
    ticks_diff: auf dem ESP32 time.ticks_diff übergeben (Überlauf von ticks_ms)
    """

    def __init__(self, names=None, timeout_ms=protocol.HEARTBEAT_TIMEOUT_MS,
                 ticks_diff=None):
        self.names = {bytes(k): v for k, v in (names or {}).items() if k}
        self.timeout_ms = timeout_ms
        self.diff = ticks_diff or _default_diff
        self.nodes = {}       # mac -> NodeState
        self.invalid = 0      # verworfene Pakete (Länge, Typ)
        self.duplicates = 0

    def _node(self, mac):
        mac = bytes(mac)
        st = self.nodes.get(mac)
        if st is None:
            st = NodeState(self.names.get(mac) or mac_str(mac))
            self.nodes[mac] = st
        return st

    def handle(self, mac, data, now_ms):
        """Eine empfangene Nachricht verarbeiten.

        Gibt ein Event zurück oder None, wenn das Paket ungültig oder doppelt war.
        Auch Lebenszeichen ergeben ein Event; sie halten den Knoten online.
        """
        try:
            pkt = protocol.unpack(data)
        except ValueError:
            self.invalid += 1
            return None

        st = self._node(mac)
        lost = 0
        if st.last_seq is not None:
            if pkt.seq == st.last_seq:
                self.duplicates += 1
                st.last_seen_ms = now_ms
                return None
            gap = protocol.lost_between(st.last_seq, pkt.seq)
            if gap <= RESTART_GAP:
                lost = gap

        came_back = st.last_seen_ms is not None and not st.online
        st.last_seq = pkt.seq
        st.last_seen_ms = now_ms
        st.online = True
        st.received += 1
        st.lost += lost
        return Event(st.name, pkt, now_ms, lost, came_back)

    def check_timeouts(self, now_ms):
        """Namen der Knoten, die gerade neu als ausgefallen erkannt wurden."""
        dropped = []
        for st in self.nodes.values():
            if st.online and self.diff(now_ms, st.last_seen_ms) > self.timeout_ms:
                st.online = False
                dropped.append(st.name)
        return dropped


def format_event(ev):
    """Ein Event als eine Terminalzeile."""
    p = ev.packet
    head = "%8d ms  %-12s #%-5d" % (ev.arrival_ms, ev.node, p.seq)
    if p.typ == protocol.TYP_COMPRESSION:
        body = "Kompression  Tiefe %5.1f mm  Frequenz %5.1f/min%s" % (
            protocol.depth_mm(p), protocol.rate_per_min(p),
            "  NICHT ENTLASTET" if protocol.not_released(p) else "")
    elif p.typ == protocol.TYP_VENTILATION:
        body = "Beatmung     Volumen %4d ml  Dauer %4d ms" % (p.wert1, p.wert2)
    else:
        body = "Lebenszeichen"
    notes = ""
    if ev.came_back:
        notes += "  (wieder da)"
    if ev.lost:
        notes += "  (%d Paket(e) verloren)" % ev.lost
    return head + body + notes
