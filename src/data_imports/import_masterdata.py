"""
Importiert Stammdaten aus einer bestehenden Excel-Datei (mit mehreren Tabellen/Excel-Tabellen) in die Projekt-SQLite-DB.
Die Ziel-DB wird automatisch im local_data_path unterhalb des Projekt-Roots angelegt (Pfad und Name aus Config).
Die Quelldatei (Excel) wird aus dem Import-Verzeichnis geladen.
Verwendet zentrale Config, Entity-Modelle aus der Config.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import openpyxl
import pandas as pd
from loguru import logger

from data_imports.normalized_masterdata import TABLES, import_normalized
from pydantic_models.config.entity_model_config import FieldConfig
from shared_modules.config import Config


def sql_type(py_type: str) -> str:
    """Mapping von Python-Typnamen (als String) auf SQLite-Typen."""
    return {"str": "TEXT", "float": "REAL", "int": "INTEGER", "bool": "INTEGER"}.get(py_type, "TEXT")


def get_type_from_str(type_str: str) -> type:
    """Wandelt einen Typnamen als String in einen Python-Typ um."""
    mapping: Dict[str, type] = {
        "str": str,
        "float": float,
        "int": int,
        "bool": bool,
    }
    return mapping.get(type_str, str)


def map_row(row: pd.Series, mapping: Dict[str, FieldConfig], required_fields: list[str]) -> Dict[str, Any]:
    """
    Mappt die Felder einer Zeile gemäß dem Mapping-Dict aus der Config.
    Führt erforderliche Typkonvertierungen durch und ergänzt fehlende Felder mit None.
    """
    result: Dict[str, Any] = {}
    for excel_col, entry in mapping.items():
        field_name = entry.name
        field_type = get_type_from_str(entry.type)
        value = row.get(excel_col)
        # Prüfe auf leere Felder (NaN, None oder leerer String)
        if (
            value is None
            or pd.isna(value)
            or (isinstance(value, str) and value.strip() == "")
        ):
            if field_type is str and not entry.optional:
                value = ""  # Leerer String für Textfelder
            else:
                value = None  # Optionale Felder und numerische Felder → NULL
        else:
            try:
                if field_type is str:
                    if isinstance(value, float) and value.is_integer():
                        value = str(int(value))
                    elif isinstance(value, (int, bool)):
                        value = str(value)
                    else:
                        value = str(value)
                # Spezialfall: multiply_by vor int-Cast anwenden (z.B. 0.5h * 60 = 30 Min)
                if entry.multiply_by is not None and field_type is int:
                    value = int(round(float(value) * entry.multiply_by))
                elif field_type is int and isinstance(value, float) and value.is_integer():
                    value = int(value)
                else:
                    value = field_type(value)
            except Exception:
                logger.warning(f"Typkonvertierung für Feld '{field_name}' fehlgeschlagen, Wert: {value}")
        result[field_name] = value
    # Fehlende Pflichtfelder ergänzen
    for field in required_fields:
        if field not in result:
            result[field] = None
    return result


def read_excel_table(file_path: Path, table_name: str) -> pd.DataFrame:
    """
    Liest eine benannte Tabelle (Excel Table, nicht Sheet!) aus einer Excel-Datei als DataFrame.
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    for ws in wb.worksheets:
        if table_name in ws.tables:
            table = ws.tables[table_name]
            ref = table.ref  # z.B. 'A1:F20'
            from openpyxl.utils.cell import range_boundaries

            min_col, min_row, max_col, max_row = range_boundaries(ref)
            data = []
            for row in ws.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
                data.append([cell.value for cell in row])
            df = pd.DataFrame(data[1:], columns=data[0])  # Erste Zeile als Header
            return df
    raise ValueError(f"Tabelle {table_name} nicht gefunden.")


# Konfigurationsnamen und physische Tabellen für das neue Workbook.

DEFAULT_TABLE_MAPPINGS = {excel: {"target": target, "entity": entity} for excel, (target, entity) in TABLES.items()}


def run_import(config: Config, source_override: Optional[Path] = None) -> int:
    """Importiert das neue Workbook; strukturell unlesbare Quellen schlagen fehl."""
    source = source_override or config.get_imports_path() / (config.database.db_name or "wegpiraten_datenbank.xlsx")
    if not source.exists():
        raise FileNotFoundError(f"Excel-Quelldatei nicht gefunden: {source}")
    return import_normalized(config, source)
