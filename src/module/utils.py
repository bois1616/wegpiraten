import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

from loguru import logger
from pydantic import BaseModel, ValidationError
from typing import List


@contextmanager
def log_exceptions(msg, continue_on_error=True):
    """
    Context-Manager für das Logging von Ausnahmen.
    Optional kann bei Fehlern abgebrochen oder weitergemacht werden.
    """
    try:
        yield
    except Exception as e:
        logger.error(f"{msg}: {e}")
        if not continue_on_error:
            raise


@contextmanager
def temporary_docx(suffix=".docx"):
    """
    Context-Manager für temporäre DOCX-Dateien.
    Die Datei wird nach Verlassen des Blocks automatisch gelöscht.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
    try:
        yield tmp_path
    finally:
        if tmp_path.exists():
            os.remove(tmp_path)


class MonthPeriod(BaseModel):
    """
    Pydantic-Modell für einen Monatszeitraum.
    Sorgt für Typsicherheit und Validierung.
    """

    start: datetime
    end: datetime


def get_month_period(abrechnungsmonat: str) -> MonthPeriod:
    """
    Gibt den ersten und letzten Tag eines Abrechnungsmonats als Pydantic-Modell zurück.
    Erwartet das Format MM.YYYY oder MM-YYYY.
    """
    abrechnungsmonat = abrechnungsmonat.replace("-", ".")
    monat, jahr = abrechnungsmonat.split(".")
    monat = int(monat)
    jahr = int(jahr)
    start = datetime(jahr, monat, 1)
    if monat == 12:
        end = datetime(jahr, 12, 31)
    else:
        # Letzter Tag im Monat = erster Tag im nächsten Monat - 1 Tag
        end = datetime(jahr, monat + 1, 1) - timedelta(days=1)
    # Rückgabe als Pydantic-Modell für Typsicherheit
    return MonthPeriod(start=start, end=end)


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


class PDFList(BaseModel):
    """
    Pydantic-Modell für eine Liste von PDF-Dateipfaden.
    Sorgt für Validierung und Typsicherheit.
    """

    pdf_files: List[Path]


def zip_invoices(pdf_files: list, zip_path: Path):
    """
    Erstellt ein ZIP-Archiv aus einer Liste von PDF-Dateien.
    Nutzt ein Pydantic-Modell zur Validierung der Dateiliste.

    Args:
        pdf_files (list): Liste von PDF-Dateipfaden.
        zip_path (Path): Zielpfad für das ZIP-Archiv.
    """
    # Validierung der Eingabe mit Pydantic
    try:
        pdf_list = PDFList(pdf_files=[Path(f) for f in pdf_files])
    except ValidationError as e:
        logger.error(f"Ungültige PDF-Dateiliste: {e}")
        raise

    with ZipFile(zip_path, "w") as zipf:
        for file in pdf_list.pdf_files:
            zipf.write(file, arcname=file.name)

# Alle Formatierungen für Zahlen, Währungen und Datumsfelder erfolgen ausschließlich im Template
# über Babel/Jinja2-Filter und die Konfiguration. Keine eigene Formatierungsfunktion mehr nötig.
