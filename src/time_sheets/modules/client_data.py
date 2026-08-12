"""
Gemeinsame DB-Abfrage aktiver Klient-Mitarbeiter-Paare für die Zeiterfassungs-Module.

Die Query (Paare aus relation_client_emp, end_date-Filter, is_active-Prüfung
für Klient/Mitarbeiter/Paar sowie employees.ts als genereller Timesheet-Schalter)
wird sowohl von TimeSheetFactory als auch von TimeSheetBatchProcessor genutzt und
ist deshalb hier zentral hinterlegt.

Die Spalten clients.employee_id/employee_2 dienen nur noch der Ansicht in der
Excel-Quelldatei und werden hier bewusst nicht mehr verwendet.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List

import pandas as pd
from loguru import logger
from pydantic import BaseModel, ValidationError

from pydantic_models.data.header_data_model import HeaderDataModel

_ACTIVE_CLIENTS_SQL = """
SELECT
    c.client_id,
    c.short_code,
    (COALESCE(c.allowed_travel_time, 0) + COALESCE(c.allowed_direct_effort, 0) + COALESCE(c.allowed_indirect_effort, 0))
        AS allowed_hours_per_month,
    COALESCE(c.allowed_travel_time, 0)    AS allowed_travel_time,
    COALESCE(c.allowed_direct_effort, 0)  AS allowed_direct_effort,
    COALESCE(c.allowed_indirect_effort, 0) AS allowed_indirect_effort,
    r.employee_id,
    c.first_name AS client_first_name,
    c.last_name AS client_last_name,
    st.code AS service_type,
    e.first_name AS employee_first_name,
    e.last_name AS employee_last_name
FROM relation_client_emp r
JOIN clients c ON r.client_id = c.client_id
JOIN employees e ON r.employee_id = e.emp_id
LEFT JOIN service_types st ON c.service_type = st.service_type_id
WHERE COALESCE(r.is_active, 1) = 1
  AND (c.end_date IS NULL OR c.end_date >= ?)
  AND COALESCE(c.is_active, 1) = 1
  AND COALESCE(e.is_active, 1) = 1
  AND c.service_type != 'ST999'
  AND COALESCE(e.ts, 1) = 1
"""
# COALESCE(e.ts, 1): TS=FALSCH sperrt jede Timesheet-Erstellung für den MA
# (klientenbezogen wie "Sonstige Aufwendungen"); ein leeres TS-Feld gilt
# dagegen weiterhin als "erstellen" (Default vor Einführung dieser Prüfung).

# Mitarbeiter mit TS=WAHR: Generiert Timesheets für "Sonstige Aufwendungen"
# (nicht klientenbezogen, z.B. Team-Tage, Weiterbildungen).
_INTERNAL_TS_SQL = """
SELECT
    e.emp_id AS employee_id,
    e.first_name AS employee_first_name,
    e.last_name AS employee_last_name
FROM employees e
WHERE COALESCE(e.ts, 0) = 1
"""

# Alle Paare aus relation_client_emp (aktiv wie inaktiv), inkl. der Felder,
# die zur Diagnose der _ACTIVE_CLIENTS_SQL-Filterbedingungen nötig sind.
_ALL_PAIRS_DIAGNOSTIC_SQL = """
SELECT
    r.client_id,
    r.employee_id,
    COALESCE(r.is_active, 1) AS pair_active,
    c.client_id AS client_found,
    COALESCE(c.is_active, 1) AS client_active,
    c.end_date,
    c.service_type,
    c.first_name AS client_first_name,
    c.last_name AS client_last_name,
    e.emp_id AS employee_found,
    COALESCE(e.is_active, 1) AS employee_active,
    COALESCE(e.ts, 1) AS employee_ts,
    e.first_name AS employee_first_name,
    e.last_name AS employee_last_name
FROM relation_client_emp r
LEFT JOIN clients c ON r.client_id = c.client_id
LEFT JOIN employees e ON r.employee_id = e.emp_id
ORDER BY r.client_id, r.employee_id
"""


class ClientEmployeePairStatus(BaseModel):
    """
    Diagnose-Eintrag für ein Klient-Mitarbeiter-Paar aus relation_client_emp:
    ob dafür im Erfassungsmonat ein Timesheet erzeugt wird, und falls nicht,
    aus welchem Grund (bzw. welchen Gründen).
    """

    client_id: str
    employee_id: str
    client_name: str = ""
    employee_name: str = ""
    included: bool
    reasons: List[str] = []


def build_pair_diagnostics(db_path: Path, reporting_month: str) -> List[ClientEmployeePairStatus]:
    """
    Liefert für JEDES Paar aus relation_client_emp (aktiv wie inaktiv) einen
    Diagnose-Eintrag. Spiegelt exakt die Filterbedingungen von
    _ACTIVE_CLIENTS_SQL, damit sich Abweichungen zwischen "Anzahl Paare" und
    "Anzahl erzeugter Timesheets" eindeutig klären lassen.
    """
    month_start = f"{reporting_month}-01"

    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(_ALL_PAIRS_DIAGNOSTIC_SQL, conn)

    entries: List[ClientEmployeePairStatus] = []
    for _, raw_row in df.iterrows():
        row = raw_row.to_dict()
        reasons: List[str] = []

        if row["pair_active"] != 1:
            reasons.append("Paar in relation_client_emp inaktiv")

        if pd.isna(row["client_found"]):
            reasons.append("client_id nicht in Stammdaten (clients) gefunden")
        else:
            if row["client_active"] != 1:
                reasons.append("Klient inaktiv")
            end_date = row["end_date"]
            if pd.notna(end_date) and str(end_date) < month_start:
                reasons.append(f"Klient-Enddatum ({end_date}) liegt vor dem Erfassungsmonat")
            if row["service_type"] == "ST999":
                reasons.append("Klient ist interner Typ ST999 (Sonstige Aufwendungen, separat über employees.ts gesteuert)")

        if pd.isna(row["employee_found"]):
            reasons.append("employee_id nicht in Stammdaten (employees) gefunden")
        else:
            if row["employee_active"] != 1:
                reasons.append("Mitarbeiter inaktiv")
            if row["employee_ts"] != 1:
                reasons.append("Mitarbeiter TS=FALSCH (keine Timesheet-Erstellung für diesen MA)")

        client_name = f"{row.get('client_first_name') or ''} {row.get('client_last_name') or ''}".strip()
        employee_name = f"{row.get('employee_first_name') or ''} {row.get('employee_last_name') or ''}".strip()

        entries.append(
            ClientEmployeePairStatus(
                client_id=str(row["client_id"]),
                employee_id=str(row["employee_id"]),
                client_name=client_name,
                employee_name=employee_name,
                included=not reasons,
                reasons=reasons,
            )
        )

    return entries


def load_active_client_headers(db_path: Path, reporting_month: str) -> List[HeaderDataModel]:
    """
    Lädt für jedes im Erfassungsmonat aktive Klient-Mitarbeiter-Paar aus
    relation_client_emp einen Header-Datensatz und validiert ihn gegen
    HeaderDataModel. Interne Klienten (service_type ST999 / Sonstige
    Aufwendungen) werden ausgeschlossen; diese werden separat über
    employees.ts gesteuert. Mitarbeiter mit employees.ts=FALSCH erhalten
    grundsätzlich keine Timesheets (weder klientenbezogen noch Sonstige
    Aufwendungen), auch wenn gültige Paare in relation_client_emp bestehen.
    """
    month_start = f"{reporting_month}-01"

    logger.info(f"Lade aktive Klient-Mitarbeiter-Paare für Monat {reporting_month}.")
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(_ACTIVE_CLIENTS_SQL, conn, params=[month_start])
    logger.info(f"{len(df)} Klient-Mitarbeiter-Paare geladen.")

    headers: List[HeaderDataModel] = []
    for idx, row in df.iterrows():
        try:
            row_dict = {str(key): value for key, value in row.to_dict().items()}
            headers.append(HeaderDataModel.model_validate(row_dict))
        except ValidationError as exc:
            logger.error(f"Ungültige Reporting-Daten in Zeile {idx}: {exc}")

    return headers


def load_internal_timesheet_headers(db_path: Path) -> List[HeaderDataModel]:
    """
    Lädt Mitarbeiter mit TS=WAHR und erzeugt HeaderDataModel für
    'Sonstige Aufwendungen' (nicht klientenbezogene Zeiten wie Team-Tage,
    Weiterbildungen).

    Die Allowed-Hours-Werte entsprechen den bisherigen CM-Klienten:
    Reise: 1000 min, Direkt: 1000 min, Indirekt: 500 min.
    """
    logger.info("Lade Mitarbeiter für Sonstige-Aufwände-Timesheets.")
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(_INTERNAL_TS_SQL, conn)
    logger.info(f"{len(df)} Mitarbeiter mit TS=WAHR gefunden.")

    headers: List[HeaderDataModel] = []
    for idx, row in df.iterrows():
        try:
            row_dict = {str(key): value for key, value in row.to_dict().items()}
            header = HeaderDataModel(
                client_id="SA",
                employee_id=row_dict["employee_id"],
                service_type="SONST",
                short_code="Sonst.Aufw.",
                allowed_hours_per_month=2500.0,
                allowed_travel_time=1000.0,
                allowed_direct_effort=1000.0,
                allowed_indirect_effort=500.0,
                employee_first_name=row_dict.get("employee_first_name"),
                employee_last_name=row_dict.get("employee_last_name"),
            )
            headers.append(header)
        except ValidationError as exc:
            logger.error(f"Ungültige Sonstige-Aufwände-Daten in Zeile {idx}: {exc}")

    return headers
