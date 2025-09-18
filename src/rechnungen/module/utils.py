import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zipfile import ZipFile

import pandas as pd
from loguru import logger

from module.invoice_context import InvoiceContext
# from module.entity import JuristischePerson, PrivatePerson

# --- Utility-Funktionen ---
def format_2f(value: float, currency: Optional[str] = None) -> str:
    """
    Formatiert einen Zahlenwert mit zwei Nachkommastellen und optionalem Währungssuffix.
    - Tausender werden mit Punkt getrennt, Dezimalstellen mit Komma.
    - Das Währungssuffix wird mit Leerzeichen angehängt, falls angegeben.

    Args:
        value (float): Der zu formatierende Zahlenwert.
        currency (str, optional): Das Währungssuffix (z.B. 'CHF'). Standard: None.

    Returns:
        str: Der formatierte Wert als String, z.B. '1.234,56 CHF'.
    """
    if pd.isna(value):
        return ""
    currency = currency or ""
    if currency and not currency.startswith(" "):
        currency = " " + currency
    tmp_val = f"{value:,.2f}"
    tmp_val = tmp_val.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{tmp_val}{currency}"

def clear_path(path: Path):
    """
    Löscht alle Dateien im angegebenen Verzeichnis.
    Unterverzeichnisse bleiben erhalten.

    Args:
        path (Path): Das Verzeichnis, dessen Dateien gelöscht werden sollen.
    """
    for item in path.iterdir():
        if item.is_file():
            item.unlink()

def zip_invoices(pdf_files: list, zip_path: Path):
    """
    Erstellt ein ZIP-Archiv aus einer Liste von PDF-Dateien.

    Args:
        pdf_files (list): Liste von PDF-Dateipfaden.
        zip_path (Path): Zielpfad für das ZIP-Archiv.
    """
    with ZipFile(zip_path, "w") as zipf:
        for file in pdf_files:
            zipf.write(file, arcname=Path(file).name)

def parse_date(date_str: str) -> str:
    """
    Parst ein Datum im Format dd.mm.YYYY und gibt es als 'YYYY-MM-DD' zurück.
    Korrigiert Eingaben wie '12.8.25' automatisch zu '12.08.2025', sofern möglich.
    """
    try:
        # Versuche zuerst das korrekte Format
        return datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
    except Exception:
        # Versuche, fehlende Nullen und kurze Jahreszahlen zu korrigieren
        parts = date_str.split(".")
        if len(parts) == 3:
            # Tag und Monat auf 2 Stellen, Jahr auf 4 Stellen bringen
            day = parts[0].zfill(2)
            month = parts[1].zfill(2)
            year = parts[2]
            # Falls Jahr nur 2 Stellen hat, ergänze '20' davor (z.B. '25' -> '2025')
            if len(year) == 2:
                year = "20" + year
            elif len(year) == 1:
                year = "200" + year
            corrected = f"{day}.{month}.{year}"
            try:
                return datetime.strptime(corrected, "%d.%m.%Y").strftime("%Y-%m-%d")
            except Exception:
                logger.error(f"Ungültiges Datumsformat nach Korrektur: '{corrected}'. Erwartet wird dd.mm.YYYY.")
        logger.error(f"Ungültiges Datumsformat: '{date_str}'. Erwartet wird dd.mm.YYYY.")
        raise ValueError(
            "Das eingegebene Datum ist leider ungültig. "
            "Bitte geben Sie das Datum im Format TT.MM.JJJJ ein, z.B. 12.08.2025."
        )

def format_date(date_str):
    """
    Wandelt YYYY-MM-DD oder ähnliche Formate in dd.mm.YYYY um.
    Gibt bei fehlerhaftem Format das Original zurück und loggt einen Fehler.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    except (ValueError, TypeError) as e:
        logger.error(f"Ungültiges Datumsformat: '{date_str}' ({e})")
        return date_str

@contextmanager
def temporary_docx(suffix=".docx"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
    try:
        yield tmp_path
    finally:
        if tmp_path.exists():
            os.remove(tmp_path)

def get_month_period(abrechnungsmonat: str) -> tuple:
    """
    Wandelt einen Abrechnungsmonat (MM.YYYY oder MM-YYYY) in Start- und Enddatum um.
    Gibt die Daten im Format 'dd.mm.YYYY' zurück.
    """
    try:
        # Erlaubt auch MM-YYYY
        abrechnungsmonat = abrechnungsmonat.replace("-", ".")
        monat, jahr = abrechnungsmonat.split(".")
        monat = int(monat)
        jahr = int(jahr)
        start = datetime(jahr, monat, 1)
        # Monatsende berechnen
        if monat == 12:
            end = datetime(jahr, 12, 31)
        else:
            end = datetime(jahr, monat + 1, 1) - timedelta(days=1)
        start_str = start.strftime("%d.%m.%Y")
        end_str = end.strftime("%d.%m.%Y")
        return start_str, end_str
    except Exception:
        raise ValueError("Bitte den Abrechnungsmonat im Format MM.YYYY eingeben.")

# Hinweis: Die Anpassung an die segmentierte config betrifft vor allem die Verwendung in anderen Modulen,
# z.B. beim Zugriff auf Spaltennamen und deren Typen. Die Utility-Funktionen selbst bleiben unverändert.
