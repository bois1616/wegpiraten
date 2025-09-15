from pathlib import Path
from typing import Optional
from zipfile import ZipFile
import pandas as pd

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
    # Formatierung: 1.234,56 statt 1,234.56
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

def zip_docs(src_dir: Path, zip_path: Path):
    """
    Erstellt ein ZIP-Archiv aller Rechnungs-DOCX-Dateien im Quellverzeichnis.
    Die Dateien werden unter ihrem Namen ins ZIP gepackt.

    Args:
        src_dir (Path): Quellverzeichnis mit den DOCX-Dateien.
        zip_path (Path): Zielpfad für das ZIP-Archiv.
    """
    with ZipFile(zip_path, "w") as zipf:
        for file in src_dir.glob("Rechnung_*.docx"):
            zipf.write(file, arcname=file.name)