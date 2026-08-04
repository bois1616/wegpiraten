"""
Erstellt die KFSG-Leistungsmeldung für die Datenbank Accordix (Kanton Bern, KJA).

Die Meldung wird auf Basis der offiziellen Excel-Vorlage
«Import-Accordix_ambulant_Excel-Format_V1.0_DE.xlsx» erzeugt, damit das
vorgegebene Format strikt eingehalten wird (Kopfzeilen 1-6, Werte-Blatt,
Wertelisten). Datenzeilen beginnen ab Zeile 7.

Quelle der Formatvorgaben:
https://www.kja.dij.be.ch/de/start/foerder--und-schutzleistungen/kantonale-datenerfassung/Datenbank_Accordix/MoeglichkeitenDatenmeldung.html

Aus der Datenbank befüllt werden: Nachname, Vorname, AHV-Nummer,
Leistungsart, Eintrittsdatum sowie das Austrittsdatum (nur wenn der
Leistungsende-Termin im oder vor dem Meldemonat liegt).
Alle übrigen Angaben (Geburtsdatum, Geschlecht, Wohnkanton, Zuweisung,
Austrittsgrund etc.) sind in der Datenbank nicht vorhanden und werden
manuell nachgetragen.
"""

import sqlite3
from datetime import date
from pathlib import Path

from loguru import logger
from openpyxl import load_workbook

from shared_modules.config import Config
from shared_modules.month_period import get_month_period
from shared_modules.utils import ensure_dir

_TEMPLATE_NAME = "Import-Accordix_ambulant_Excel-Format_V1.0_DE.xlsx"
_SHEET_NAME = "Ambulant"
_FIRST_DATA_ROW = 7  # Kopfzeilen/Hinweise stehen in den Zeilen 1-6

# Spalten gemäss Vorlage (Zeile 4 enthält die technischen Feldnamen)
_COL_LAST_NAME = "A"  # LastName
_COL_FIRST_NAME = "B"  # FirstName
_COL_AHV = "C"  # SocialInsuranceNumber
_COL_SERVICE_TYPE = "L"  # ServiceTypeName
_COL_START_DATE = "Q"  # StartDate
_COL_END_DATE = "S"  # EndDate

# Mapping service_types.code -> Accordix-Leistungsart.
# Zielstrings entsprechen exakt der Werteliste im Blatt «Werte» der Vorlage.
# Nicht gelistete Leistungsarten (Privatleistungen, Sonstige Aufwendungen,
# Jugendcoaching, Abklärung, Berichte) sind nicht KFSG-meldepflichtig bzw.
# nicht zuordenbar und werden mit Warnung übersprungen.
_SERVICE_TYPE_MAP: dict[str, str] = {
    "SPF": "Sozialpädagogische Familienbegleitung (SPF)",
    "UWB  (Ausübung Gruppe)": "Besuchsrecht - Begleitung bei Ausübung Besuchsrecht (Gruppensetting)",
    "UWB (Übergabe Gruppe)": "Besuchsrecht - Begleitung bei Kinderübergabe (Gruppensetting)",
    "UWB (Begleitung Individuell)": "Besuchsrecht (individuelle Begleitung)",
    "DAF L": "DAF: Begleitung von Pflegeverhältnissen Langzeitunterbringung",
}

_SQL = """
SELECT
    c.client_id,
    c.last_name,
    c.first_name,
    c.social_security_number,
    c.start_date,
    c.end_date,
    st.code AS service_code
FROM clients c
LEFT JOIN service_types st ON c.service_type = st.service_type_id
WHERE date(c.start_date) <= date(:period_end)
  AND (c.end_date IS NULL OR date(c.end_date) >= date(:period_start))
ORDER BY c.last_name, c.first_name
"""


def _parse_db_date(value: str | None) -> date | None:
    """Wandelt einen DB-Datumsstring ('YYYY-MM-DD ...') in ein date um."""
    if not value:
        return None
    return date.fromisoformat(value.strip()[:10])


def _format_date(value: date) -> str:
    """Formatiert ein Datum gemäss Vorlage als TT.MM.JJJJ (Text)."""
    return value.strftime("%d.%m.%Y")


def create_accordix_report(config: Config, reporting_month: str) -> Path:
    """
    Erstellt die Accordix-Leistungsmeldung (ambulant) für einen Meldemonat.

    Enthalten sind alle Klient:innen, deren Leistung im Meldemonat aktiv war
    (start_date <= Monatsende und end_date offen oder >= Monatsanfang) und
    deren Leistungsart auf eine Accordix-Leistungsart abbildbar ist.

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
        rows = conn.execute(
            _SQL,
            {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
            },
        ).fetchall()

    if not rows:
        logger.warning("Keine aktiven Klient:innen für {} gefunden.", month_str)
        raise ValueError(f"Keine aktiven Klient:innen für {month_str} gefunden.")

    # load_workbook verwirft die x14-Datenvalidierungs-Erweiterung der Vorlage
    # (Dropdown-Komfort); das strikt einzuhaltende Importformat (Zellinhalte)
    # bleibt davon unberührt.
    workbook = load_workbook(template_path)
    sheet = workbook[_SHEET_NAME]

    written = 0
    skipped = 0
    for row in rows:
        client_id, last_name, first_name, ahv, start_raw, end_raw, service_code = row

        service_name = _SERVICE_TYPE_MAP.get(service_code or "")
        if service_name is None:
            skipped += 1
            logger.warning(
                "Klient {} ({} {}) übersprungen: Leistungsart {!r} ist keiner "
                "Accordix-Leistungsart zugeordnet.",
                client_id,
                last_name,
                first_name,
                service_code,
            )
            continue

        start_date = _parse_db_date(start_raw)
        if start_date is None:
            skipped += 1
            logger.warning(
                "Klient {} ({} {}) übersprungen: kein gültiges Eintrittsdatum.",
                client_id,
                last_name,
                first_name,
            )
            continue

        end_date = _parse_db_date(end_raw)

        excel_row = _FIRST_DATA_ROW + written
        sheet[f"{_COL_LAST_NAME}{excel_row}"] = last_name
        sheet[f"{_COL_FIRST_NAME}{excel_row}"] = first_name
        if ahv:
            sheet[f"{_COL_AHV}{excel_row}"] = ahv
        sheet[f"{_COL_SERVICE_TYPE}{excel_row}"] = service_name
        sheet[f"{_COL_START_DATE}{excel_row}"] = _format_date(start_date)
        # Austrittsdatum nur setzen, wenn die Leistung im oder vor dem
        # Meldemonat endet; andernfalls läuft die Leistung weiter (leer).
        if end_date is not None and end_date <= period_end:
            sheet[f"{_COL_END_DATE}{excel_row}"] = _format_date(end_date)
        written += 1

    if written == 0:
        raise ValueError(
            f"Keine meldepflichtigen Leistungen für {month_str} gefunden "
            f"({skipped} Klient:innen übersprungen)."
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
