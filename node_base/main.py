"""Hauptschleife der Basisstation (ESP-NOW-Empfang).

Stand M1: empfängt die Pakete der Sensorknoten, decodiert sie und gibt sie
im Terminal aus. Fällt ein Knoten 3 s lang aus, erscheint eine Meldung.

Auf das Board kopieren (flach, ohne Ordner):
    common/protocol.py, common/config.py, node_base/receiver.py, node_base/main.py
z. B. mit:
    mpremote cp common/protocol.py common/config.py node_base/receiver.py node_base/main.py :
"""

import time

import espnow
import network

import config
from receiver import Receiver, format_event, mac_str

RECV_TIMEOUT_MS = 100  # so oft wird spätestens auf Ausfälle geprüft


def setup_radio():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.disconnect()  # ESP-NOW braucht keine WLAN-Verbindung
    sta.config(channel=config.WIFI_CHANNEL)
    e = espnow.ESPNow()
    e.active(True)
    print("Basisstation MAC:", mac_str(sta.config("mac")),
          " Kanal:", config.WIFI_CHANNEL)
    return e


def main():
    e = setup_radio()
    rx = Receiver(
        names={
            config.MAC_COMPRESSION: "Kompression",
            config.MAC_VENTILATION: "Beatmung",
        },
        ticks_diff=time.ticks_diff,
    )
    print("Warte auf Pakete ...")

    while True:
        mac, msg = e.recv(RECV_TIMEOUT_MS)
        now = time.ticks_ms()
        if msg:
            ev = rx.handle(mac, msg, now)
            if ev:
                print(format_event(ev))
        for name in rx.check_timeouts(now):
            print("%8d ms  AUSFALL: %s sendet seit %d s nichts"
                  % (now, name, rx.timeout_ms // 1000))


main()
