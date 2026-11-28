"""ESP-NOW einrichten. Läuft nur auf dem ESP32 (network, espnow).

Gemeinsam für alle drei Knoten, damit Kanal und Peers überall gleich sind.
"""

import espnow
import network

import config

BROADCAST = b"\xff" * 6


def mac_str(mac):
    return ":".join("%02x" % b for b in mac)


def setup(name):
    """WLAN-Station aktivieren, Kanal setzen, ESP-NOW starten.

    Gibt das ESPNow-Objekt zurück und druckt die eigene MAC, damit sie in
    config.py eingetragen werden kann.
    """
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.disconnect()  # ESP-NOW braucht keine WLAN-Verbindung
    sta.config(channel=config.WIFI_CHANNEL)
    e = espnow.ESPNow()
    e.active(True)
    print("%s MAC: %s  Kanal: %d"
          % (name, mac_str(sta.config("mac")), config.WIFI_CHANNEL))
    return e


def base_peer(e):
    """Basisstation als Peer eintragen und ihre Adresse zurückgeben.

    Solange config.MAC_BASE leer ist, wird per Broadcast gesendet. Dann gibt
    es keine Empfangsbestätigung, ein Ausfall der Basis fällt also nicht auf.
    """
    peer = config.MAC_BASE or BROADCAST
    e.add_peer(peer)
    if peer == BROADCAST:
        print("MAC_BASE leer -> sende per Broadcast")
    else:
        print("Sende an Basisstation", mac_str(peer))
    return peer
