"""Zielwerte und Schwellen (Frequenz, Tiefe, Entlastung, Hands-off, Volumen, Insufflationsdauer).

Außerdem die Funkeinstellungen, die alle drei Knoten teilen.
"""

# --- Funk (ESP-NOW) -------------------------------------------------------
# Am Integrationstermin (30.11.) festlegen. Alle Knoten müssen denselben
# WLAN-Kanal nutzen.
WIFI_CHANNEL = 1

# MAC-Adressen der Knoten als 6 Bytes, z. B. b"\x24\x0a\xc4\x12\x34\x56".
# Jeder Knoten gibt seine MAC beim Start aus. Solange ein Eintrag leer ist,
# zeigt die Basisstation den Absender als MAC-Adresse an.
MAC_COMPRESSION = b""
MAC_VENTILATION = b""
MAC_BASE = b""
