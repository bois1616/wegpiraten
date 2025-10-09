import os
import re
import tempfile
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple
from zipfile import ZipFile

from loguru import logger
from openpyxl.utils.cell import coordinate_from_string
from pydantic import BaseModel, ValidationError, field_validator


def clear_path(path: Path) -> None:
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

    @field_validator("pdf_files")
    def all_files_must_exist(cls, v: List[Path]) -> List[Path]:
        """
        Validiert, dass alle angegebenen Dateien existieren.
        """
        for file in v:
            if not file.exists():
                raise ValueError(f"Datei nicht gefunden: {file}")
        return v

def zip_invoices(pdf_files: List[Path], zip_path: Path) -> None:
    """
    Erstellt ein ZIP-Archiv aus einer Liste von PDF-Dateien.
    Nutzt ein Pydantic-Modell zur Validierung der Dateiliste.

    Args:
        pdf_files (List[Path]): Liste von PDF-Dateipfaden.
        zip_path (Path): Zielpfad für das ZIP-Archiv.
    """
    # Validierung der Eingabe mit Pydantic
    try:
        pdf_list = PDFList(pdf_files=pdf_files)
    except ValidationError as e:
        logger.error(f"Ungültige PDF-Dateiliste: {e}")
        raise

    with ZipFile(zip_path, "w") as zipf:
        for file in pdf_list.pdf_files:
            zipf.write(file, arcname=file.name)

def safe_str(val) -> str:
    """
    Gibt immer einen String zurück, auch wenn val None oder numerisch ist.
    """
    return "" if val is None else str(val)


@contextmanager
def log_exceptions(msg: str, continue_on_error: bool = True) -> Generator[None, None, None]:
    """
    Context-Manager für das Logging von Ausnahmen.
    Loggt eine Fehlermeldung und entscheidet, ob die Exception weitergereicht wird.

    Args:
        msg (str): Nachricht für das Logging im Fehlerfall.
        continue_on_error (bool): Bei False wird die Exception erneut ausgelöst, ansonsten nur geloggt.

    Beispiel:
        with log_exceptions("Fehler beim Verarbeiten der Datei"):
            do_something()
    """
    try:
        yield
    except Exception as e:
        logger.error(f"{msg}: {e}")
        if not continue_on_error:
            raise

@contextmanager
def temporary_docx(suffix: str = ".docx") -> Generator[Path, None, None]:
    """
    Context-Manager für temporäre DOCX-Dateien.
    Die Datei wird nach Verlassen des Blocks automatisch gelöscht.

    Args:
        suffix (str): Dateiendung für die temporäre Datei (Standard: ".docx").

    Yields:
        Path: Pfad zur temporären Datei.

    Beispiel:
        with temporary_docx() as tmp_path:
            # Schreibe in tmp_path
            ...
        # Nach dem Block wird die Datei gelöscht.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
    try:
        yield tmp_path
    finally:
        if tmp_path.exists():
            os.remove(tmp_path)

# Hilfsfunktion für Typumwandlung (wird für dynamische Modell-Erzeugung benötigt)
def get_type_from_str(type_str: str):
    mapping = {
        "str": str,
        "float": float,
        "int": int,
        "bool": bool,
    }
    return mapping.get(type_str, str)


# Datumsformate für freie Texteingaben
DATE_FORMATS: tuple[str, ...] = ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d", "%m.%Y")

def _parse_float_str(s: str) -> Optional[float]:
    s = s.strip().replace("’", "").replace("'", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def _parse_date_str(s: str) -> Optional[date]:
    s = s.strip()
    for fmt in DATE_FORMATS:
        try:
            d = datetime.strptime(s, fmt)
            if fmt == "%m.%Y":
                d = d.replace(day=1)
            return d.date()
        except ValueError:
            continue
    return None

_FLOAT_CONVERTERS: Dict[type, Callable[[Any], Optional[float]]] = {
    type(None): lambda _v: None,
    int: lambda v: float(v),
    float: lambda v: float(v),
    str: _parse_float_str,
}

_DATE_CONVERTERS: Dict[type, Callable[[Any], Optional[date]]] = {
    datetime: lambda v: v.date(),
    date: lambda v: v,
    str: _parse_date_str,
    type(None): lambda _v: None,
}

def to_float(v: Any) -> Optional[float]:
    """Typbasierte Zahl-Konvertierung (None/str/int/float -> float|None)."""
    conv = _FLOAT_CONVERTERS.get(type(v))
    return conv(v) if conv else None

def to_date(v: Any) -> Optional[date]:
    """Typbasierte Datums-Konvertierung (None/str/date/datetime -> date|None)."""
    conv = _DATE_CONVERTERS.get(type(v))
    return conv(v) if conv else None

def to_year_month_str(v: Any) -> Optional[str]:
    """Konvertiert Eingabe nach YYYY-MM (falls Datum ermittelbar)."""
    d = to_date(v)
    return d.strftime("%Y-%m") if d else None

def choose_existing_path(candidates: list[Optional[Path]], fallback: Path) -> Path:
    """Gibt den ersten existierenden Pfad aus candidates zurück, sonst fallback."""
    for p in candidates:
        if p and p.exists():
            return p
    return fallback

def ensure_dir(path: Path) -> Path:
    """Erzeugt ein Verzeichnis (rekursiv), falls es fehlt, und gibt den Pfad zurück."""
    path.mkdir(parents=True, exist_ok=True)
    return path
# Hinweis: Alle Formatierungen für Zahlen, Währungen und Datumsfelder erfolgen ausschließlich im Template
# über Babel/Jinja2-Filter und die Konfiguration. Keine eigene Formatierungsfunktion mehr nötig.

_CELL_RE = re.compile(r"^[A-Za-z]+[0-9]+$")

def split_cell_address(address: str) -> Tuple[str, int]:
    addr = address.strip().upper()
    if not _CELL_RE.match(addr):
        raise ValueError(f"Ungültige Zelladresse: {address}")
    col, row = coordinate_from_string(addr)
    return col, int(row)

def derive_table_range(start_cell: str, end_cell: str) -> Tuple[str, int, str, int]:
    start_col, start_row = split_cell_address(start_cell)
    end_col, end_row = split_cell_address(end_cell)
    if end_row < start_row:
        raise ValueError("time_sheet_data_end_cell liegt oberhalb von time_sheet_data_start_cell")
    return start_col, start_row, end_col, end_row
