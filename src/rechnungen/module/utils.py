import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile
import numpy as np

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

def get_month_period(abrechnungsmonat: str) -> tuple[datetime, datetime]:
    """
    Gibt den ersten und letzten Tag eines Abrechnungsmonats zurück.
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
    return start, end

def explode_context(context: dict) -> dict:
    def to_dict(obj):
        # Primitive Typen inkl. numpy-Typen direkt zurückgeben
        if isinstance(obj, (str, int, float, bool, type(None), np.generic)):
            return obj
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "as_dict") and callable(obj.as_dict):
            return obj.as_dict()
        # Listen von Objekten (z.B. Positionen) als Liste von dicts
        if isinstance(obj, list):
            return [to_dict(item) for item in obj]
        return {k: v for k, v in vars(obj).items() if not k.startswith("_") and not callable(v)}
    
    exploded = {}
    for k, v in context.items():
        if k == "Positionen" and isinstance(v, list):
            exploded[k] = v
        else:
            exploded[k] = to_dict(v)
    return exploded

# Alle Formatierungen für Zahlen, Währungen und Datumsfelder erfolgen ausschließlich im Template
# über Babel/Jinja2-Filter und die Konfiguration. Keine eigene Formatierungsfunktion mehr nötig.
