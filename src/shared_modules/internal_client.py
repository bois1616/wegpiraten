"""
Sentinel-Klient «SA» für nicht klientenbezogene Zeiten (Sonstige Aufwendungen).

Team-Tage, Weiterbildungen und ähnliche Aufwände werden auf diesen Klienten
gebucht. Er steht bewusst nicht in der Excel-Stammdatendatei, weil er weder
fakturiert noch an Accordix gemeldet wird — der Stammdaten-Import legt ihn
deshalb selbst an, damit der Timesheet-Import die FK-Prüfung gegen
clients.client_id besteht.
"""

from typing import Any, Dict

INTERNAL_CLIENT_ID = "SA"
INTERNAL_SERVICE_TYPE_ID = "ST999"
INTERNAL_SERVICE_TYPE_CODE = "SONST"
INTERNAL_SHORT_CODE = "Sonst.Aufw."
INTERNAL_CLIENT_LAST_NAME = "Sonstige Aufwendungen"

# Budgetwerte in Minuten, identisch zu den Werten im erzeugten SA-Timesheet.
INTERNAL_ALLOWED_TRAVEL_TIME = 1000
INTERNAL_ALLOWED_DIRECT_EFFORT = 1000
INTERNAL_ALLOWED_INDIRECT_EFFORT = 500
INTERNAL_ALLOWED_HOURS_PER_MONTH = 2500.0

# Nur gesetzte Felder; alle übrigen Spalten der Tabelle clients bleiben NULL.
# tenant_id, payer_id und service_requester_id müssen NULL bleiben, sonst
# schlägt die FK-Prüfung fehl.
INTERNAL_CLIENT_FIELDS: Dict[str, Any] = {
    "client_id": INTERNAL_CLIENT_ID,
    "first_name": "",
    "last_name": INTERNAL_CLIENT_LAST_NAME,
    "short_code": INTERNAL_SHORT_CODE,
    "service_type": INTERNAL_SERVICE_TYPE_ID,
    "allowed_travel_time": INTERNAL_ALLOWED_TRAVEL_TIME,
    "allowed_direct_effort": INTERNAL_ALLOWED_DIRECT_EFFORT,
    "allowed_indirect_effort": INTERNAL_ALLOWED_INDIRECT_EFFORT,
}
