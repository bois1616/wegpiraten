"""
Importiert Stammdaten aus einer bestehenden Excel-Datei (mit mehreren Tabellen/Excel-Tabellen) in die Projekt-SQLite-DB.
Die Ziel-DB wird automatisch im local_data_path unterhalb des Projekt-Roots angelegt (Pfad und Name aus Config).
Die Quelldatei (Excel) wird aus shared_data_path geladen.
Verwendet zentrale Config, Entity-Modelle aus der Config.
"""

import sqlite3
import openpyxl
import pandas as pd
from pathlib import Path
from typing import Dict, Type, Any
from loguru import logger

from shared_modules.config import Config
from shared_modules.config_data import FieldConfig


def sql_type(py_type: str) -> str:
    # Mapping von Python-Typnamen (als String) auf SQLite-Typen
    return {"str": "TEXT", "float": "REAL", "int": "INTEGER", "bool": "INTEGER"}.get(
        py_type, "TEXT"
    )


def create_target_tables(conn, table_mappings, field_mappings):
    """
    Erstellt die Zieltabelle(n) in der SQLite-DB anhand der Felddefinitionen im Modell.
    Der Primärschlüssel wird aus den Feldern mit primary_key: true im field_mappings bestimmt.
    """
    cur = conn.cursor()
    for excel_table, table_cfg in table_mappings.items():
        target_table = table_cfg["target"]
        entity = table_cfg["entity"]
        fields = field_mappings[entity]
        columns = []
        primary_keys = []
        for excel_col, entry in fields.items():
            col_name = entry.field
            col_type = sql_type(entry.type)
            if getattr(entry, "primary_key", False):
                primary_keys.append(col_name)
            columns.append(f"{col_name} {col_type}")
        columns_sql = ",\n    ".join(columns)
        pk_sql = ""
        if primary_keys:
            pk_sql = f",\n    PRIMARY KEY ({', '.join(primary_keys)})"
        sql = (
            f"CREATE TABLE IF NOT EXISTS {target_table} (\n    {columns_sql}{pk_sql}\n)"
        )
        cur.execute(sql)
    conn.commit()


def get_type_from_str(type_str: str):
    """
    Wandelt einen Typnamen als String in einen Python-Typ um.
    """
    mapping = {
        "str": str,
        "float": float,
        "int": int,
        "bool": bool,
    }
    return mapping.get(type_str, str)


def map_row(
    row: pd.Series, mapping: Dict[str, FieldConfig], required_fields: list
) -> Dict[str, Any]:
    """
    Mappt die Felder einer Zeile gemäß dem Mapping-Dict aus der Config.
    Führt erforderliche Typkonvertierungen durch und ergänzt fehlende Felder mit None.
    """
    result = {}
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
                logger.warning(
                    f"Typkonvertierung für Feld '{field_name}' fehlgeschlagen, Wert: {value}"
                )
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
            min_col, min_row, max_col, max_row = openpyxl.utils.range_boundaries(ref)
            data = []
            for row in ws.iter_rows(
                min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col
            ):
                data.append([cell.value for cell in row])
            df = pd.DataFrame(data[1:], columns=data[0])  # Erste Zeile als Header
            return df
    raise ValueError(f"Tabelle {table_name} nicht gefunden.")


def import_table(
    source_excel: Path,
    target_conn: sqlite3.Connection,
    table_name: str,
    target_table: str,
    model: Type,
    mapping: Dict[str, FieldConfig],
) -> None:
    """
    Liest alle Daten aus der angegebenen Excel-Tabelle (nicht Sheet!), mappt die Felder und schreibt sie in die Zieltabelle.
    """
    logger.info(f"Importiere Excel-Tabelle {table_name} → {target_table}")
    try:
        excel_table = read_excel_table(source_excel, table_name)
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Excel-Tabelle {table_name}: {e}")
        return

    required_fields = list(model.model_fields.keys())
    records = []
    for _, row in excel_table.iterrows():
        if row.isnull().all():
            continue
        try:
            mapped = map_row(row, mapping, required_fields)
            rec = model(**mapped)
            records.append(rec.model_dump())
        except Exception as e:
            logger.error(
                f"Fehler beim Validieren eines Datensatzes aus {table_name}: {e}"
            )

    if records:
        df_target = pd.DataFrame(records)
        try:
            df_target.to_sql(target_table, target_conn, if_exists="append", index=False)
            logger.success(f"{len(df_target)} Datensätze in {target_table} importiert.")
        except Exception as e:
            logger.error(f"Fehler beim Schreiben in {target_table}: {e}")
    else:
        logger.warning(f"Keine gültigen Datensätze für {target_table} gefunden.")


def main() -> None:
    """
    Hauptfunktion: Liest die Konfiguration, legt die Ziel-DB an (falls erforderlich),
    legt die Tabellen an und importiert die Stammdaten.
    """
    # Lade zentrale Konfiguration
    config_path = (
        Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"
    )
    config = Config()
    config.load(config_path)

    # Zugriff auf Pydantic-Modelle immer per Punktnotation!
    prj_root = Path(config.data.structure.prj_root)
    shared_data_path = Path(config.data.structure.shared_data_path)
    local_data_path = Path(config.data.structure.local_data_path)
    # SQLite-DB-Name und Excel-Dateiname ggf. aus database-Config holen
    sqlite_db_name = (
        config.data.database.sqlite_db_name
        if config.data.database and config.data.database.sqlite_db_name
        else "Wegpiraten Datenbank.sqlite3"
    )
    db_name = (
        config.data.database.db_name
        if config.data.database and config.data.database.db_name
        else "Wegpiraten Datenbank.xlsx"
    )

    # Setze die Pfade für die Quelldatei (Excel) und die Zieldatenbank (SQLite)
    source_excel_path = shared_data_path / db_name
    target_db_path = prj_root / local_data_path / sqlite_db_name

    table_mappings = config.data.table_mappings
    entity_models = config.get_entity_models()  # zentrale Modell-Erzeugung

    TABLES = {}
    for excel_table, table_cfg in table_mappings.items():
        entity = table_cfg["entity"]
        model_config = config.data.models[entity]
        # Mapping: excel_column → FieldConfig
        mapping = {f.excel_column: f for f in model_config.fields if f.excel_column}
        TABLES[excel_table] = {
            "target": table_cfg["target"],
            "model": entity_models[entity],
            "mapping": mapping,
        }

    with sqlite3.connect(target_db_path) as target_conn:
        # Passe create_target_tables an, um Felder aus config.data.models zu verwenden
        def create_target_tables(conn, table_mappings, models):
            cur = conn.cursor()
            for excel_table, table_cfg in table_mappings.items():
                target_table = table_cfg["target"]
                entity = table_cfg["entity"]
                fields = models[entity].fields
                columns = []
                primary_keys = []
                for field in fields:
                    col_name = field.name
                    col_type = sql_type(field.type)
                    if hasattr(field, "primary_key") and field.primary_key:
                        primary_keys.append(col_name)
                    columns.append(f"{col_name} {col_type}")
                columns_sql = ",\n    ".join(columns)
                pk_sql = ""
                if primary_keys:
                    pk_sql = f",\n    PRIMARY KEY ({', '.join(primary_keys)})"
                sql = f"CREATE TABLE IF NOT EXISTS {target_table} (\n    {columns_sql}{pk_sql}\n)"
                cur.execute(sql)
            conn.commit()

        create_target_tables(
            conn=target_conn, table_mappings=table_mappings, models=config.data.models
        )
        for source_table, meta in TABLES.items():
            try:
                import_table(
                    source_excel=source_excel_path,
                    target_conn=target_conn,
                    table_name=source_table,
                    target_table=meta["target"],
                    model=meta["model"],
                    mapping=meta["mapping"],
                )
            except Exception as e:
                logger.error(f"Fehler beim Import von {source_table}: {e}")
    logger.info("Stammdaten-Import abgeschlossen.")


if __name__ == "__main__":
    main()
