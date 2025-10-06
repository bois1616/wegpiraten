
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List
from zipfile import ZipFile

from loguru import logger
from pydantic import BaseModel, ValidationError, field_validator
import os
import tempfile


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

# Hinweis: Alle Formatierungen für Zahlen, Währungen und Datumsfelder erfolgen ausschließlich im Template
# über Babel/Jinja2-Filter und die Konfiguration. Keine eigene Formatierungsfunktion mehr nötig.
