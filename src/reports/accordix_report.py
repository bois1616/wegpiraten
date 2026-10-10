"""
Erstellt die KFSG-Leistungsmeldung für die Datenbank Accordix (Kanton Bern, KJA).

Die Meldung wird auf Basis der offiziellen Excel-Vorlage
«Import-Accordix_ambulant_Excel-Format_V1.0_DE.xlsx» erzeugt, damit das
vorgegebene Format strikt eingehalten wird (Kopfzeilen 1-6, Werte-Blatt,
Wertelisten). Datenzeilen beginnen ab Zeile 7.

Quelle der Formatvorgaben:
https://www.kja.dij.be.ch/de/start/foerder--und-schutzleistungen/kantonale-datenerfassung/Datenbank_Accordix/MoeglichkeitenDatenmeldung.html

Befüllt werden alle Felder, die in den Klienten-Stammdaten gepflegt sind:
Nachname, Vorname, AHV-Nummer, Geburtsdatum, Geschlecht, UMA/UMF,
Hauptsprache, Wohnkanton, Wohnort Sorgeberechtigte, Leistungsart,
Zuweisung, Eintrittsdatum sowie das Austrittsdatum (nur wenn das
Leistungsende im oder vor dem Meldemonat liegt).
Die Austrittsfelder (war geplant, Austrittsgrund, Situation nach Austritt)
sind Ereignisdaten und werden im Meldefile manuell nachgetragen.
"""

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from openpyxl import load_workbook

from shared_modules.accordix import (
    FIELD_VALUE_LISTS,
    SERVICE_TYPE_MAP,
    missing_required_fields,
    parse_db_date,
    validate_coded_value,
)
from shared_modules.config import Config
from shared_modules.internal_client import INTERNAL_SERVICE_TYPE_ID
from shared_modules.month_period import get_month_period
from shared_modules.utils import ensure_dir

_TEMPLATE_NAME = "Import-Accordix_ambulant_Excel-Format_V1.0_DE.xlsx"
_SHEET_NAME = "Ambulant"
_FIRST_DATA_ROW = 7  # Kopfzeilen/Hinweise stehen in den Zeilen 1-6

# Spalten gemäss Vorlage (Zeile 4 enthält die technischen Feldnamen)
_COL_LAST_NAME = "A"  # LastName
_COL_FIRST_NAME = "B"  # FirstName
_COL_AHV = "C"  # SocialInsuranceNumber
_COL_DATE_OF_BIRTH = "D"  # DateOfBirth
_COL_GENDER = "E"  # Gender
_COL_UMA_UMF = "F"  # UmaUmfRecognition
_COL_LANGUAGE = "G"  # SpokenLanguage
_COL_CANTON = "I"  # CantonOfResidence
_COL_RESIDENCE = "J"  # ResidenceLegalGuardian
_COL_SERVICE_TYPE = "L"  # ServiceTypeName
_COL_ALLOCATION = "M"  # Allocation
_COL_START_DATE = "Q"  # StartDate
_COL_END_DATE = "S"  # EndDate

_SQL_BASE = """
SELECT b.mandate_id AS client_id, b.person_id,
    p.last_name, p.first_name, p.social_security_number, p.date_of_birth,
    p.gender, p.uma_umf, p.spoken_language, p.canton_of_residence,
    p.residence_legal_guardian, m.allocation, b.start_date, b.end_date,
    b.is_leaving_reason_planned, b.leaving_reason, b.custom_leaving_reason,
    b.after_leave_situation, b.custom_after_leave_situation,
    b.is_consultative_adolescent_psychiatric_care, b.number_of_care_days_per_week,
    b.remarks, st.code AS service_code, m.predecessor_mandate_id,
    m.start_date AS mandate_start, m.payer_id
FROM mandate_person b
LEFT JOIN person p ON b.person_id=p.person_id
LEFT JOIN mandate m ON b.mandate_id=m.mandate_id
LEFT JOIN service_types st ON m.service_type_id=st.service_type_id
WHERE date(m.start_date)<=date(:period_end)
  AND (m.end_date IS NULL OR date(m.end_date)>=date(:period_start))
  AND (b.end_date IS NULL OR date(b.end_date)>=date(:period_start))
ORDER BY p.last_name,p.first_name,m.start_date,b.source_row
"""


def _collapse_continuing_cares(
    conn: sqlite3.Connection, rows: list[dict[str, Any]], payers: list[str]
) -> list[dict[str, Any]]:
    """Ein Folgeauftrag erzeugt für dieselbe fortlaufende Betreuung keine zweite Zeile."""
    all_cares = conn.execute("""SELECT b.mandate_id,b.person_id,date(b.start_date),
        m.predecessor_mandate_id,st.code FROM mandate_person b
        JOIN mandate m ON b.mandate_id=m.mandate_id
        LEFT JOIN service_types st ON m.service_type_id=st.service_type_id""").fetchall()
    by_key = {(r[0], r[1]): r for r in all_cares}
    chosen: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        if row["payer_id"] not in payers:
            continue
        current = by_key.get((row["client_id"], row["person_id"]))
        root = row["client_id"]
        seen: set[str] = set()
        while current and current[3] and root not in seen:
            seen.add(root)
            previous = by_key.get((current[3], row["person_id"]))
            if not previous or previous[2] != current[2] or previous[4] != current[4]:
                break
            root = previous[0]
            current = previous
        if current and current[3] and root in seen:
            logger.warning(
                "Betreuung {}: zyklische Auftragskette, Meldezeile zur Nacharbeit ausgelassen", row["person_id"]
            )
            continue
        key = (root, row["person_id"], row["service_code"], str(row["start_date"])[:10])
        if key in chosen:
            logger.info("Fortlaufende Betreuung {}: Folgeaufträge zu einer Accordix-Zeile zusammengefasst", key)
        chosen[key] = row
    return list(chosen.values())


def _format_date(value: date) -> str:
    """Formatiert ein Datum gemäss Vorlage als TT.MM.JJJJ (Text)."""
    return value.strftime("%d.%m.%Y")


def _set_if_present(sheet, column: str, excel_row: int, value: Optional[Any]) -> None:
    """Schreibt einen Wert in eine Zelle, sofern er nicht leer ist."""
    if value is not None and str(value).strip() != "":
        sheet[f"{column}{excel_row}"] = str(value).strip()


def create_accordix_report(config: Config, reporting_month: str) -> Path:
    """
    Erstellt die Accordix-Leistungsmeldung (ambulant) für einen Meldemonat.

    Enthalten sind alle Klient:innen, deren Leistung im Meldemonat aktiv war
    (start_date <= Monatsende und end_date offen oder >= Monatsanfang), deren
    Leistungsart auf eine Accordix-Leistungsart abbildbar ist und deren
    Accordix-Pflichtfelder vollständig sind. Unvollständige Datensätze werden
    mit Angabe der fehlenden Felder übersprungen.

    Args:
        config: Konfigurationsobjekt.
        reporting_month: Meldemonat (beliebiges Format MM.YYYY / MM-YYYY / YYYY-MM).

    Returns:
        Pfad zur erzeugten Excel-Datei.
    """
    period = get_month_period(reporting_month)
    month_str = period.start.strftime("%Y-%m")
    period_start = period.start.date()
    period_end = period.end.date()

    template_path = config.get_template_path(_TEMPLATE_NAME)
    if not template_path.exists():
        raise FileNotFoundError(f"Accordix-Vorlage nicht gefunden: {template_path}")

    db_path = config.get_db_path()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            _SQL_BASE,
            {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "internal_service_type": INTERNAL_SERVICE_TYPE_ID,
            },
        )
        column_names = [desc[0] for desc in cursor.description]
        rows = [dict(zip(column_names, row)) for row in cursor.fetchall()]
        rows = _collapse_continuing_cares(conn, rows, config.reporting.accordix_payer_ids)

    if not rows:
        logger.warning("Keine aktiven Klient:innen für {} gefunden.", month_str)
        logger.warning("Leere Accordix-Meldung: keine passenden Betreuungen für {}", month_str)

    # load_workbook verwirft die x14-Datenvalidierungs-Erweiterung der Vorlage
    # (Dropdown-Komfort); das strikt einzuhaltende Importformat (Zellinhalte)
    # bleibt davon unberührt.
    workbook = load_workbook(template_path)
    sheet = workbook[_SHEET_NAME]

    written = 0
    skipped = 0
    for row in rows:
        client_id = row["client_id"]
        label = f"{row['last_name']} {row['first_name']}"

        service_name = SERVICE_TYPE_MAP.get(row["service_code"] or "")
        if service_name is None:
            skipped += 1
            logger.warning(
                "Klient {} ({}) übersprungen: Leistungsart {!r} ist keiner Accordix-Leistungsart zugeordnet.",
                client_id,
                label,
                row["service_code"],
            )
            continue

        start_date = parse_db_date(row["start_date"])
        if start_date is None:
            skipped += 1
            logger.warning(
                "Klient {} ({}) übersprungen: kein gültiges Eintrittsdatum.",
                client_id,
                label,
            )
            continue

        missing = missing_required_fields(row)
        if missing:
            skipped += 1
            logger.warning(
                "Klient {} ({}) übersprungen: fehlende Accordix-Pflichtfelder: {}. "
                "Bitte in den Stammdaten nachtragen und 'import-master' ausführen.",
                client_id,
                label,
                ", ".join(missing),
            )
            continue

        invalid = [
            f"{field}: {error}"
            for field in FIELD_VALUE_LISTS
            if (error := validate_coded_value(field, row.get(field))) is not None
        ]
        if invalid:
            skipped += 1
            logger.warning(
                "Klient {} ({}) übersprungen: ungültige Werte: {}. "
                "Bitte in den Stammdaten korrigieren und 'import-master' ausführen.",
                client_id,
                label,
                "; ".join(invalid),
            )
            continue

        end_date = parse_db_date(row["end_date"])

        excel_row = _FIRST_DATA_ROW + written
        sheet[f"{_COL_LAST_NAME}{excel_row}"] = row["last_name"]
        sheet[f"{_COL_FIRST_NAME}{excel_row}"] = row["first_name"]
        _set_if_present(sheet, _COL_AHV, excel_row, row["social_security_number"])
        date_of_birth = parse_db_date(row.get("date_of_birth"))
        if date_of_birth is not None:
            sheet[f"{_COL_DATE_OF_BIRTH}{excel_row}"] = _format_date(date_of_birth)
        _set_if_present(sheet, _COL_GENDER, excel_row, row.get("gender"))
        _set_if_present(sheet, _COL_UMA_UMF, excel_row, row.get("uma_umf"))
        _set_if_present(sheet, _COL_LANGUAGE, excel_row, row.get("spoken_language"))
        _set_if_present(sheet, _COL_CANTON, excel_row, row.get("canton_of_residence"))
        _set_if_present(sheet, _COL_RESIDENCE, excel_row, row.get("residence_legal_guardian"))
        sheet[f"{_COL_SERVICE_TYPE}{excel_row}"] = service_name
        _set_if_present(sheet, _COL_ALLOCATION, excel_row, row.get("allocation"))
        sheet[f"{_COL_START_DATE}{excel_row}"] = _format_date(start_date)
        if end_date is not None and end_date <= period_end:
            sheet[f"{_COL_END_DATE}{excel_row}"] = _format_date(end_date)
            for column, field in (
                ("T", "is_leaving_reason_planned"),
                ("U", "leaving_reason"),
                ("V", "custom_leaving_reason"),
                ("W", "after_leave_situation"),
                ("X", "custom_after_leave_situation"),
            ):
                _set_if_present(sheet, column, excel_row, row.get(field))
        for column, field in (
            ("N", "is_consultative_adolescent_psychiatric_care"),
            ("O", "number_of_care_days_per_week"),
            ("Z", "remarks"),
        ):
            _set_if_present(sheet, column, excel_row, row.get(field))
        written += 1

    if written == 0:
        logger.warning(
            "Keine gültige Accordix-Zeile für {}, {} Betreuungen zur Nacharbeit ausgelassen", month_str, skipped
        )

    output_path = ensure_dir(config.get_output_path())
    out_file = output_path / f"Accordix_ambulant_{month_str}.xlsx"
    workbook.save(out_file)

    logger.info(
        "Accordix-Meldung geschrieben: {} ({} Zeilen, {} übersprungen)",
        out_file,
        written,
        skipped,
    )
    return out_file
