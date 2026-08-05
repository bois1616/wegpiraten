"""
Zentrale Accordix-Definitionen für die KFSG-Leistungsmeldung (Kanton Bern, KJA).

Bündelt die verbindlichen Wertelisten aus der offiziellen Excel-Vorlage
(Blatt «Werte»), das Mapping der internen Leistungsarten auf
Accordix-Leistungsarten sowie Validierungsfunktionen, die sowohl beim
Stammdaten-Import als auch bei der Erstellung der Meldedatei verwendet
werden.

Quelle der Wertelisten:
templates/Import-Accordix_ambulant_Excel-Format_V1.0_DE.xlsx (Blatt «Werte»)
"""

from datetime import date, datetime
from typing import Any, Optional

# Mapping service_types.code -> Accordix-Leistungsart.
# Zielstrings entsprechen exakt der Werteliste im Blatt «Werte» der Vorlage.
# Nicht gelistete Leistungsarten (Privatleistungen, Sonstige Aufwendungen,
# Jugendcoaching, Abklärung, Berichte) sind nicht KFSG-meldepflichtig bzw.
# nicht zuordenbar.
SERVICE_TYPE_MAP: dict[str, str] = {
    "SPF": "Sozialpädagogische Familienbegleitung (SPF)",
    "UWB  (Ausübung Gruppe)": "Besuchsrecht - Begleitung bei Ausübung Besuchsrecht (Gruppensetting)",
    "UWB (Übergabe Gruppe)": "Besuchsrecht - Begleitung bei Kinderübergabe (Gruppensetting)",
    "UWB (Begleitung Individuell)": "Besuchsrecht (individuelle Begleitung)",
    "DAF L": "DAF: Begleitung von Pflegeverhältnissen Langzeitunterbringung",
}

# Wertelisten gemäss Blatt «Werte» der Accordix-Vorlage
GENDER_VALUES: tuple[str, ...] = ("m", "w", "d")
UMA_UMF_VALUES: tuple[str, ...] = ("Ja", "Nein", "Unbekannt")
LANGUAGE_VALUES: tuple[str, ...] = ("DE", "FR")
CANTON_VALUES: tuple[str, ...] = (
    "AG", "AI", "AR", "BE", "BL", "BS", "FR", "GE", "GL", "GR", "JU", "LU",
    "NE", "NW", "OW", "SG", "SH", "SO", "SZ", "TG", "TI", "UR", "VD", "VS",
    "ZG", "ZH", "Ausland",
)
ALLOCATION_VALUES: tuple[str, ...] = (
    "Einvernehmlich über Sozialdienst",
    "KESB (zusammen mit Gericht)",
    "Jugendanwaltschaft",
)

# Austrittsgründe (ambulant und stationär)
LEAVING_REASON_VALUES: tuple[str, ...] = (
    "Abbruch durch Sorgeberechtigte/Leistungsempfänger",
    "Abbruch durch Leistungsbesteller (KESB, Sozialdienst, Jugendanwaltschaft)",
    "Abbruch durch KESB aufgrund Volljährigkeit",
    "Abbruch durch Leistungserbringer aufgrund Konfliktsituationen",
    "Abbruch durch Leistungserbringer aufgrund kurzfristig notwendigen Wechsels des Leistungsangebots",
    "Anderer",
)

# Situation nach Austritt (ambulant)
AFTER_LEAVE_SITUATION_VALUES: tuple[str, ...] = (
    "weitere ambulante Leistung bei aktuellem Leistungserbringer",
    "weitere ambulante Leistung bei anderem Leistungserbringer",
    "stationäre Einrichtung",
    "Pflegefamilie",
    "keine weitere Leistung",
    "andere",
)

# Zusätzliche Klienten-Stammdatenfelder für Accordix
# (Excel-Spaltenname in masterdata_client = Spaltenname in der DB-Tabelle clients)
ACCORDIX_CLIENT_FIELDS: tuple[str, ...] = (
    "date_of_birth",
    "gender",
    "uma_umf",
    "spoken_language",
    "canton_of_residence",
    "residence_legal_guardian",
    "allocation",
    "is_consultative_adolescent_psychiatric_care",
    "number_of_care_days_per_week",
    "is_leaving_reason_planned",
    "leaving_reason",
    "custom_leaving_reason",
    "after_leave_situation",
    "custom_after_leave_situation",
    "remarks",
)

# Pflichtfelder in Accordix (ohne diese ist eine Meldezeile ungültig)
REQUIRED_CLIENT_FIELDS: tuple[str, ...] = (
    "date_of_birth",
    "gender",
    "uma_umf",
    "canton_of_residence",
)

# Zulässige Werte je Codefeld (für Import-Validierung und Excel-Dropdowns)
FIELD_VALUE_LISTS: dict[str, tuple[str, ...]] = {
    "gender": GENDER_VALUES,
    "uma_umf": UMA_UMF_VALUES,
    "spoken_language": LANGUAGE_VALUES,
    "canton_of_residence": CANTON_VALUES,
    "allocation": ALLOCATION_VALUES,
    "leaving_reason": LEAVING_REASON_VALUES,
    "after_leave_situation": AFTER_LEAVE_SITUATION_VALUES,
}


def parse_db_date(value: Any) -> Optional[date]:
    """
    Wandelt einen DB-/Excel-Datumswert in ein date um.

    Akzeptiert date, datetime sowie Strings im Format 'YYYY-MM-DD ...'
    (So speichert der Stammdaten-Import Excel-Datumszellen).
    Gibt None zurück, wenn der Wert leer oder nicht interpretierbar ist.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def validate_coded_value(field: str, value: Any) -> Optional[str]:
    """
    Prüft ein Codefeld gegen die Accordix-Werteliste.

    Returns:
        Fehlermeldung oder None, wenn der Wert leer oder zulässig ist.
    """
    allowed = FIELD_VALUE_LISTS.get(field)
    if allowed is None:
        return None
    if value is None or str(value).strip() == "":
        return None
    if str(value).strip() not in allowed:
        return f"ungültiger Wert {value!r} (erlaubt: {', '.join(allowed)})"
    return None


def check_date_consistency(
    date_of_birth: Optional[date],
    start_date: Optional[date],
    end_date: Optional[date],
) -> list[str]:
    """
    Prüft die Konsistenz der Datumsfelder eines Klienten.

    Returns:
        Liste von Warnmeldungen (leer, wenn alles konsistent ist).
    """
    warnings: list[str] = []
    if date_of_birth is not None:
        if date_of_birth > date.today():
            warnings.append(f"Geburtsdatum {date_of_birth} liegt in der Zukunft")
        if start_date is not None and start_date < date_of_birth:
            warnings.append(
                f"Leistungsbeginn {start_date} liegt vor dem Geburtsdatum {date_of_birth}"
            )
    if start_date is not None and end_date is not None and end_date < start_date:
        warnings.append(f"Enddatum {end_date} liegt vor dem Leistungsbeginn {start_date}")
    return warnings


def missing_required_fields(row: dict[str, Any]) -> list[str]:
    """
    Liefert die Accordix-Pflichtfelder, die in einem Klienten-Datensatz fehlen.

    date_of_birth gilt nur als vorhanden, wenn es als Datum interpretierbar ist.
    """
    missing: list[str] = []
    for field in REQUIRED_CLIENT_FIELDS:
        value = row.get(field)
        if field == "date_of_birth":
            if parse_db_date(value) is None:
                missing.append(field)
        elif value is None or str(value).strip() == "":
            missing.append(field)
    return missing
