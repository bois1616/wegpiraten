"""
Importiert Stammdaten aus einer bestehenden Excel-Datei (mit mehreren Tabellen/Excel-Tabellen) in die Projekt-SQLite-DB.
Die Ziel-DB wird automatisch im local_data_path unterhalb des Projekt-Roots angelegt (Pfad und Name aus Config).
Die Quelldatei (Excel) wird aus shared_data_path geladen.
Verwendet zentrale Config, Entity-Modelle aus der Config.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

import openpyxl
import pandas as pd
from loguru import logger

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
            or (isinstance(value, float) and pd.isna(value))
            or (isinstance(value, str) and value.strip() == "")
        ):
            if field_type is str:
                value = ""  # Leerer String für Textfelder
            else:
                value = None  # Für numerische Felder bleibt es None!
        else:
            try:
                # Spezialfall: float auf int, falls nötig
                if field_type is int and isinstance(value, float) and value.is_integer():
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


def create_target_tables(
    conn: sqlite3.Connection,
    entity_name: str,
    target_table: str,
    fields: list[FieldConfig],
) -> None:
    """
    Erstellt die Zieltabelle in der SQLite-DB anhand der Felddefinitionen.
    """
    cur = conn.cursor()
    columns = []
    primary_keys = []
    for field in fields:
        col_name = field.name
        col_type = sql_type(field.type)
        if field.primary_key:
            primary_keys.append(col_name)
        columns.append(f"{col_name} {col_type}")

    columns_sql = ",\n    ".join(columns)
    pk_sql = ""
    if primary_keys:
        pk_sql = f",\n    PRIMARY KEY ({', '.join(primary_keys)})"
    sql = f"CREATE TABLE IF NOT EXISTS {target_table} (\n    {columns_sql}{pk_sql}\n)"
    logger.debug(f"Erstelle Tabelle {target_table}: {sql}")
    cur.execute(sql)
    conn.commit()


def import_entity_data(
    source_excel: Path,
    target_conn: sqlite3.Connection,
    excel_table_name: str,
    target_table: str,
    fields: list[FieldConfig],
) -> int:
    """
    Liest alle Daten aus der angegebenen Excel-Tabelle, mappt die Felder und schreibt sie in die Zieltabelle.
    Gibt die Anzahl der importierten Datensätze zurück.
    """
    logger.info(f"Importiere Excel-Tabelle {excel_table_name} → {target_table}")
    try:
        excel_table = read_excel_table(source_excel, excel_table_name)
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Excel-Tabelle {excel_table_name}: {e}")
        return 0

    # Mapping: excel_column → FieldConfig
    mapping = {f.excel_column: f for f in fields if f.excel_column}
    required_fields = [f.name for f in fields]

    records = []
    for _, row in excel_table.iterrows():
        if row.isnull().all():
            continue
        try:
            mapped = map_row(row, mapping, required_fields)
            records.append(mapped)
        except Exception as e:
            logger.error(f"Fehler beim Validieren eines Datensatzes: {e}")

    if records:
        df_target = pd.DataFrame(records)
        try:
            df_target.to_sql(target_table, target_conn, if_exists="append", index=False)
            logger.success(f"{len(df_target)} Datensätze in {target_table} importiert.")
            return len(df_target)
        except Exception as e:
            logger.error(f"Fehler beim Schreiben in {target_table}: {e}")
            return 0
    else:
        logger.warning(f"Keine gültigen Datensätze für {target_table} gefunden.")
        return 0


# Standard-Tabellen-Mapping (Excel-Tabellenname → SQLite-Tabelle, Entity-Name)
DEFAULT_TABLE_MAPPINGS = {
    "MD_MA": {"target": "employees", "entity": "employee"},
    "Leistungsbesteller": {"target": "service_requester", "entity": "service_requester"},
    "Zahlungsdienstleister": {"target": "payer", "entity": "payer"},
    "MD_Client": {"target": "clients", "entity": "client"},
}


def run_import(config: Config, source_override: Optional[Path] = None) -> int:
    """
    Führt den Stammdaten-Import durch.

    Args:
        config: Die Konfiguration
        source_override: Optionaler Pfad zur Excel-Quelldatei (überschreibt Config)

    Returns:
        Anzahl der insgesamt importierten Datensätze
    """
    # Pfade aus Config
    prj_root = Path(config.structure.prj_root)
    shared_data_path = Path(config.structure.shared_data_path or "")
    local_data_path = config.structure.local_data_path or "data"

    # Dateinamen
    sqlite_db_name = config.database.sqlite_db_name or "Wegpiraten Datenbank.sqlite3"
    db_name = config.database.db_name or "Wegpiraten Datenbank.xlsx"

    # Quelldatei und Ziel-DB
    if source_override:
        source_excel_path = source_override
    else:
        source_excel_path = shared_data_path / db_name

    target_db_path = prj_root / local_data_path / sqlite_db_name

    if not source_excel_path.exists():
        raise FileNotFoundError(f"Excel-Quelldatei nicht gefunden: {source_excel_path}")

    logger.info(f"Importiere Stammdaten von {source_excel_path} nach {target_db_path}")

    total_imported = 0
    with sqlite3.connect(target_db_path) as target_conn:
        for excel_table, table_cfg in DEFAULT_TABLE_MAPPINGS.items():
            entity_name = table_cfg["entity"]
            target_table = table_cfg["target"]

            # Entity-Felder aus Config holen
            entity_config = config.models.get(entity_name)
            if not entity_config:
                logger.warning(f"Entity '{entity_name}' nicht in Config gefunden, überspringe.")
                continue

            fields = entity_config.fields

            # Tabelle erstellen
            create_target_tables(target_conn, entity_name, target_table, fields)

            # Daten importieren
            try:
                count = import_entity_data(
                    source_excel=source_excel_path,
                    target_conn=target_conn,
                    excel_table_name=excel_table,
                    target_table=target_table,
                    fields=fields,
                )
                total_imported += count
            except Exception as e:
                logger.error(f"Fehler beim Import von {excel_table}: {e}")

    logger.info(f"Stammdaten-Import abgeschlossen. {total_imported} Datensätze importiert.")
    return total_imported


def main() -> None:
    """Hauptfunktion: Liest die Konfiguration und importiert die Stammdaten."""
    config = Config()
    run_import(config)


if __name__ == "__main__":
    main()
