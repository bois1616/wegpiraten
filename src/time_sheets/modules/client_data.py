"""
Gemeinsame DB-Abfrage aktiver Klienten für die Zeiterfassungs-Module.

Die Query (inkl. employee_2-Logik, end_date-Filter und is_active-Prüfung)
wird sowohl von TimeSheetFactory als auch von TimeSheetBatchProcessor genutzt
und ist deshalb hier zentral hinterlegt.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List

import pandas as pd
from loguru import logger
from pydantic import ValidationError

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
    c.employee_id,
    c.employee_2,
    c.first_name AS client_first_name,
    c.last_name AS client_last_name,
    st.code AS service_type,
    e.first_name AS employee_first_name,
    e.last_name AS employee_last_name,
    e2.first_name AS employee_2_first_name,
    e2.last_name AS employee_2_last_name
FROM clients c
LEFT JOIN employees e  ON c.employee_id = e.emp_id
LEFT JOIN employees e2 ON c.employee_2  = e2.emp_id
LEFT JOIN service_types st ON c.service_type = st.service_type_id
WHERE (c.end_date IS NULL OR c.end_date >= ?)
  AND COALESCE(c.is_active, 1) = 1
  AND c.service_type != 'ST999'
"""

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


def load_active_client_headers(db_path: Path, reporting_month: str) -> List[HeaderDataModel]:
    """
    Lädt alle im Erfassungsmonat aktiven Klienten mitsamt Mitarbeiterdaten
    und validiert sie gegen HeaderDataModel.
    Für Klienten mit employee_2 wird ein zweiter Header-Datensatz ergänzt.
    Interne Klienten (service_type ST999 / Sonstige Aufwendungen) werden ausgeschlossen;
    diese werden separat über employees.ts gesteuert.
    """
    month_start = f"{reporting_month}-01"

    logger.info(f"Lade aktive Klienten für Monat {reporting_month}.")
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(_ACTIVE_CLIENTS_SQL, conn, params=[month_start])
    logger.info(f"{len(df)} Klientendatensätze geladen.")

    headers: List[HeaderDataModel] = []
    for idx, row in df.iterrows():
        try:
            row_dict = {str(key): value for key, value in row.to_dict().items()}
            headers.append(HeaderDataModel.model_validate(row_dict))
            # Zweites Timesheet für employee_2, falls vorhanden
            emp2_id = row_dict.get("employee_2")
            if emp2_id and pd.notna(emp2_id) and str(emp2_id).strip():
                row2 = dict(row_dict)
                row2["employee_id"] = str(emp2_id).strip()
                row2["employee_first_name"] = row_dict.get("employee_2_first_name")
                row2["employee_last_name"] = row_dict.get("employee_2_last_name")
                headers.append(HeaderDataModel.model_validate(row2))
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
