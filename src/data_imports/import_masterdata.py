"""
Importiert Stammdaten aus einer bestehenden Excel-Datei (mit mehreren Tabellen/Excel-Tabellen) in die Projekt-SQLite-DB.
Die Ziel-DB wird automatisch im local_data_path unterhalb des Projekt-Roots angelegt (Pfad und Name aus Config).
Die Quelldatei (Excel) wird aus dem Import-Verzeichnis geladen.
Verwendet zentrale Config, Entity-Modelle aus der Config.
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
import pandas as pd
from loguru import logger

from pydantic_models.config.entity_model_config import FieldConfig
from shared_modules.config import Config
from shared_modules.internal_client import INTERNAL_CLIENT_FIELDS, INTERNAL_CLIENT_ID
from shared_modules.utils import ensure_dir


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


def create_target_tables(
    conn: sqlite3.Connection,
    entity_name: str,
    target_table: str,
    fields: list[FieldConfig],
    foreign_keys: Optional[list[tuple[str, str, str]]] = None,
) -> None:
    """
    Erstellt die Zieltabelle in der SQLite-DB anhand der Felddefinitionen.
    """
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (target_table,))
    table_exists = cur.fetchone() is not None
    columns = []
    primary_keys = []
    for field in fields:
        col_name = field.name
        col_type = sql_type(field.type)
        if field.primary_key:
            primary_keys.append(col_name)
        columns.append(f"{col_name} {col_type}")

    if "is_active" not in {field.name for field in fields}:
        columns.append("is_active INTEGER NOT NULL DEFAULT 1")

    columns_sql = ",\n    ".join(columns)
    pk_sql = ""
    if primary_keys:
        pk_sql = f",\n    PRIMARY KEY ({', '.join(primary_keys)})"
    fk_sql = ""
    if foreign_keys:
        fk_clauses = [
            f"FOREIGN KEY ({column}) REFERENCES {ref_table}({ref_column})"
            for column, ref_table, ref_column in foreign_keys
        ]
        fk_sql = ",\n    " + ",\n    ".join(fk_clauses)
    sql = f"CREATE TABLE IF NOT EXISTS {target_table} (\n    {columns_sql}{pk_sql}{fk_sql}\n)"
    logger.debug(f"Erstelle Tabelle {target_table}: {sql}")
    cur.execute(sql)

    if table_exists:
        existing_columns = {row[1] for row in cur.execute(f"PRAGMA table_info({target_table})").fetchall()}
        desired_columns = [(field.name, sql_type(field.type)) for field in fields]
        if "is_active" not in {field.name for field in fields}:
            desired_columns.append(("is_active", "INTEGER NOT NULL DEFAULT 1"))

        for col_name, col_type in desired_columns:
            if col_name in existing_columns:
                continue
            alter_sql = f"ALTER TABLE {target_table} ADD COLUMN {col_name} {col_type}"
            logger.info("Erweitere Tabelle {} um Spalte {} ({})", target_table, col_name, col_type)
            cur.execute(alter_sql)

        if foreign_keys:
            logger.warning(f"Tabelle {target_table} existiert bereits. Foreign Keys wurden nicht nachträglich gesetzt.")

    conn.commit()


def _fetch_fk_reference_values(conn: sqlite3.Connection, ref_table: str, ref_column: str) -> set[str]:
    """Liest alle vorhandenen (nicht leeren) Werte einer Referenzspalte für FK-Prüfungen."""
    try:
        cur = conn.execute(f"SELECT {ref_column} FROM {ref_table}")
    except sqlite3.OperationalError as exc:
        logger.warning("FK-Referenzwerte nicht lesbar: {}.{} ({})", ref_table, ref_column, exc)
        return set()
    return {str(row[0]).strip() for row in cur.fetchall() if row[0] is not None and str(row[0]).strip() != ""}


def _build_internal_client_record(fields: list[FieldConfig]) -> Dict[str, Any]:
    """Baut den Sentinel-Klienten 'SA' als regulären Stammdatensatz."""
    record: Dict[str, Any] = {field.name: None for field in fields}
    record.update(INTERNAL_CLIENT_FIELDS)
    return record


def import_entity_data(
    source_excel: Path,
    target_conn: sqlite3.Connection,
    excel_table_name: str,
    target_table: str,
    fields: list[FieldConfig],
    foreign_keys: Optional[list[tuple[str, str, str]]] = None,
) -> Tuple[int, int, int, Dict[str, List[str]]]:
    """
    Liest alle Daten aus der angegebenen Excel-Tabelle, mappt die Felder und schreibt sie in die Zieltabelle.
    Gibt die Anzahl der importierten Datensätze zurück.
    """
    logger.info(f"Importiere Excel-Tabelle {excel_table_name} → {target_table}")
    try:
        excel_table = read_excel_table(source_excel, excel_table_name)
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Excel-Tabelle {excel_table_name}: {e}")
        return 0, 0, 0, {"inserted": [], "updated": [], "deactivated": []}

    # Mapping: excel_column → FieldConfig
    mapping = {f.excel_column: f for f in fields if f.excel_column}
    required_fields = [f.name for f in fields]

    # Referenzwerte für alle FK-Spalten einmalig vorladen, damit ungültige
    # FK-Werte (Tippfehler, gelöschte Referenzen) VOR dem INSERT erkannt und
    # einzeln übersprungen werden – statt erst als SQLite-IntegrityError
    # aufzufallen und dabei den kompletten executemany-Batch (inkl. aller
    # danach folgenden, gültigen Datensätze) abzubrechen.
    fk_reference_cache: Dict[Tuple[str, str], set[str]] = {}
    for _, ref_table, ref_column in foreign_keys or []:
        cache_key = (ref_table, ref_column)
        if cache_key not in fk_reference_cache:
            fk_reference_cache[cache_key] = _fetch_fk_reference_values(target_conn, ref_table, ref_column)

    pk_fields = [field.name for field in fields if field.primary_key]
    records: List[Dict[str, Any]] = []
    seen_keys: set[Tuple[Any, ...]] = set()
    for _, row in excel_table.iterrows():
        if row.isnull().all():
            continue
        try:
            mapped = map_row(row, mapping, required_fields)
            pk_key = _pk_key(mapped, pk_fields)
            if pk_key is None:
                logger.error("Datensatz ohne Primärschlüssel in {} übersprungen.", target_table)
                continue
            if pk_key in seen_keys:
                logger.error("Doppelter Primärschlüssel in {} übersprungen: {}", target_table, _format_pk(pk_key))
                continue
            seen_keys.add(pk_key)
            if foreign_keys:
                optional_fields = {f.name for f in fields if f.optional}
                missing_fk_fields: List[str] = []
                invalid_fk_fields: List[str] = []
                for column, ref_table, ref_column in foreign_keys:
                    value = mapped.get(column)
                    is_blank = value is None or (isinstance(value, str) and value.strip() == "")
                    if is_blank:
                        if column not in optional_fields:
                            missing_fk_fields.append(column)
                        continue
                    valid_values = fk_reference_cache.get((ref_table, ref_column), set())
                    if str(value).strip() not in valid_values:
                        invalid_fk_fields.append(f"{column}={value!r} (nicht in {ref_table}.{ref_column})")
                if missing_fk_fields:
                    pk_values = {field: mapped.get(field) for field in pk_fields} if pk_fields else {}
                    logger.error(
                        "Datensatz übersprungen ({}): fehlende FK-Felder {}. PK={}",
                        target_table,
                        ", ".join(missing_fk_fields),
                        pk_values or "n/a",
                    )
                    continue
                if invalid_fk_fields:
                    pk_values = {field: mapped.get(field) for field in pk_fields} if pk_fields else {}
                    logger.error(
                        "Datensatz übersprungen ({}): ungültige FK-Werte {}. PK={}",
                        target_table,
                        ", ".join(invalid_fk_fields),
                        pk_values or "n/a",
                    )
                    continue
            records.append(mapped)
        except Exception as e:
            logger.error(f"Fehler beim Validieren eines Datensatzes: {e}")

    if not records:
        logger.warning(f"Keine gültigen Datensätze für {target_table} gefunden.")
        return 0, 0, 0, {"inserted": [], "updated": [], "deactivated": []}

    if target_table == "clients":
        _validate_client_accordix(records)
        if any(str(rec.get("client_id") or "").strip() == INTERNAL_CLIENT_ID for rec in records):
            logger.warning(
                "Klient '{}' steht bereits in den Excel-Stammdaten; der systemseitige Datensatz "
                "für Sonstige Aufwendungen wird nicht ergänzt.",
                INTERNAL_CLIENT_ID,
            )
        else:
            records.append(_build_internal_client_record(fields))

    select_cols = [field.name for field in fields]
    if "is_active" not in select_cols:
        select_cols.append("is_active")

    existing_rows = _load_existing_rows(target_conn, target_table, select_cols, pk_fields)
    existing_by_key = {row["_pk_key"]: row for row in existing_rows}

    incoming_by_key: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    for row in records:
        key = _pk_key(row, pk_fields)
        if key is None:
            continue
        incoming_by_key[key] = row

    inserted: List[str] = []
    updated: List[str] = []
    deactivated: List[str] = []

    inserted_count = 0
    updated_count = 0
    deactivated_count = 0

    # Inserts
    insert_cols = [field.name for field in fields] + ["is_active"]
    insert_sql = f"INSERT INTO {target_table} ({', '.join(insert_cols)}) VALUES ({', '.join(['?'] * len(insert_cols))})"
    insert_values: List[Tuple[Any, ...]] = []

    for key, row in incoming_by_key.items():
        if key not in existing_by_key:
            values = [row.get(col) for col in insert_cols if col != "is_active"] + [1]
            insert_values.append(tuple(values))
            inserted.append(_format_pk(key))

    # Updates / Reactivations
    update_keys = set(incoming_by_key.keys()) & set(existing_by_key.keys())
    for key in update_keys:
        incoming = incoming_by_key[key]
        existing = existing_by_key[key]
        changes = _diff_row(existing, incoming, fields)
        set_cols = list(changes.keys())
        set_values = [incoming.get(col) for col in set_cols]
        if existing.get("is_active") != 1:
            set_cols.append("is_active")
            set_values.append(1)
            changes.setdefault("is_active", f"{existing.get('is_active')} → 1")

        if set_cols:
            set_clause = ", ".join([f"{col}=?" for col in set_cols])
            where_clause, where_values = _pk_where_clause(pk_fields, key)
            sql = f"UPDATE {target_table} SET {set_clause} WHERE {where_clause}"
            target_conn.execute(sql, (*set_values, *where_values))
            updated.append(_format_pk(key) + _format_changes(changes))
            updated_count += 1

    # Deactivate missing
    missing_keys = set(existing_by_key.keys()) - set(incoming_by_key.keys())
    for key in missing_keys:
        if key is None:
            continue
        existing = existing_by_key.get(key, {})
        if existing.get("is_active") == 0:
            continue
        where_clause, where_values = _pk_where_clause(pk_fields, key)
        sql = f"UPDATE {target_table} SET is_active = 0 WHERE {where_clause}"
        target_conn.execute(sql, where_values)
        deactivated.append(_format_pk(key))
        deactivated_count += 1

    if insert_values:
        try:
            target_conn.executemany(insert_sql, insert_values)
            inserted_count = len(insert_values)
        except Exception as exc:
            _log_import_diagnostics(target_conn, target_table, pd.DataFrame(records), fields)
            raise exc

    logger.success(
        f"{inserted_count} eingefügt, {updated_count} aktualisiert, {deactivated_count} deaktiviert in {target_table}."
    )

    return (
        inserted_count,
        updated_count,
        deactivated_count,
        {
            "inserted": inserted,
            "updated": updated,
            "deactivated": deactivated,
        },
    )


def _validate_client_accordix(records: List[Dict[str, Any]]) -> None:
    """
    Prüft die Accordix-Felder der Klienten-Datensätze (nur Warnungen, kein Abbruch).

    - Codefelder gegen die Accordix-Wertelisten
    - Datums-Konsistenz (Geburtsdatum, Leistungsbeginn, Enddatum)
    - Widersprüche zwischen Datensätzen derselben Person (gleiche AHV-Nr.,
      unterschiedliche Personendaten, z.B. bei mehreren Leistungen)
    """
    from shared_modules.accordix import (
        FIELD_VALUE_LISTS,
        check_date_consistency,
        parse_db_date,
        validate_coded_value,
    )

    for record in records:
        client_id = record.get("client_id") or "?"
        for field in FIELD_VALUE_LISTS:
            error = validate_coded_value(field, record.get(field))
            if error:
                logger.warning("Klient {}: Feld {}: {}", client_id, field, error)
        for warning in check_date_consistency(
            parse_db_date(record.get("date_of_birth")),
            parse_db_date(record.get("start_date")),
            parse_db_date(record.get("end_date")),
        ):
            logger.warning("Klient {}: {}", client_id, warning)

    # Personendaten-Konsistenz über alle Zeilen mit gleicher AHV-Nr.
    person_fields = ("date_of_birth", "gender", "uma_umf", "spoken_language", "canton_of_residence")
    by_ahv: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        ahv = str(record.get("social_security_number") or "").strip()
        if ahv:
            by_ahv.setdefault(ahv, []).append(record)
    for ahv, group in by_ahv.items():
        if len(group) < 2:
            continue
        for field in person_fields:
            values = {str(rec.get(field) or "").strip() for rec in group} - {""}
            if len(values) > 1:
                ids = [rec.get("client_id") for rec in group]
                logger.warning(
                    "AHV {}: widersprüchliche Werte für {} bei {}: {}",
                    ahv,
                    field,
                    ids,
                    sorted(values),
                )


# Standard-Tabellen-Mapping (Excel-Tabellenname → SQLite-Tabelle, Entity-Name)
DEFAULT_TABLE_MAPPINGS = {
    "masterdata_employee": {"target": "employees", "entity": "employee"},
    "masterdata_payer": {"target": "payer", "entity": "payer"},
    "masterdata_service_requester": {"target": "service_requester", "entity": "service_requester"},
    "masterdata_tenant": {"target": "masterdata_tenant", "entity": "tenant"},
    "service_types": {"target": "service_types", "entity": "service_type"},
    "masterdata_client": {"target": "clients", "entity": "client"},
    # Relation Klient<->Mitarbeiter; muss nach masterdata_client und
    # masterdata_employee importiert werden (FK-Referenzen), daher hier am Ende.
    "relation_client_emp": {"target": "relation_client_emp", "entity": "client_employee_relation"},
}

FOREIGN_KEY_MAPPINGS: Dict[str, list[tuple[str, str, str]]] = {
    "clients": [
        ("tenant_id", "masterdata_tenant", "tenant_id"),
        ("payer_id", "payer", "payer_id"),
        ("service_requester_id", "service_requester", "service_requester_id"),
        ("service_type", "service_types", "service_type_id"),
    ],
    "relation_client_emp": [
        ("client_id", "clients", "client_id"),
        ("employee_id", "employees", "emp_id"),
    ],
}


def _log_import_diagnostics(
    target_conn: sqlite3.Connection,
    target_table: str,
    df_target: pd.DataFrame,
    fields: list[FieldConfig],
) -> None:
    pk_fields = [field.name for field in fields if field.primary_key]
    if pk_fields:
        duplicates = df_target[df_target.duplicated(subset=pk_fields, keep=False)]
        if not duplicates.empty:
            dup_df: pd.DataFrame = duplicates.loc[:, pk_fields]
            sample = dup_df.head(5).to_dict(orient="records")
            logger.error(
                "Doppelte Primärschlüssel in {} gefunden ({} Zeilen). Beispiele: {}",
                target_table,
                len(duplicates),
                sample,
            )

    optional_field_names = {f.name for f in fields if f.optional}
    for column, ref_table, ref_column in FOREIGN_KEY_MAPPINGS.get(target_table, []):
        is_optional = column in optional_field_names
        if column not in df_target.columns:
            logger.warning(
                "FK-Prüfung übersprungen: Spalte {} fehlt in {}.",
                column,
                target_table,
            )
            continue
        series = df_target[column]
        blanks = series.isna() | series.astype(str).str.strip().eq("")
        blank_count = int(blanks.sum())
        if blank_count and not is_optional:
            logger.error(
                "FK-Spalte {} enthält {} leere Werte (NULL/leer).",
                column,
                blank_count,
            )
        values = set(series[~blanks].astype(str))
        ref_values = _fetch_fk_reference_values(target_conn, ref_table, ref_column)
        missing = sorted(values - ref_values)
        if missing:
            sample_missing = missing[:10]
            filtered_df: pd.DataFrame = df_target.loc[
                df_target[column].astype(str).isin(sample_missing),
                [column],
            ]
            sample_rows = filtered_df.head(5).to_dict(orient="records")
            logger.error(
                "FK-Verletzung in {}.{}: {} fehlende Werte (z.B. {}). Beispiele Zeilen: {}",
                target_table,
                column,
                len(missing),
                sample_missing,
                sample_rows,
            )


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
    imports_path = config.get_imports_path()
    local_data_path = config.structure.local_data_path or "data"

    # Dateinamen
    sqlite_db_name = config.database.sqlite_db_name or "Wegpiraten Datenbank.sqlite3"
    db_name = config.database.db_name or "Wegpiraten Datenbank.xlsx"

    if source_override:
        source_excel_path = source_override
    else:
        source_excel_path = imports_path / db_name
        if not source_excel_path.exists() and Path(db_name).suffix.lower() == ".xlsx":
            source_excel_path = imports_path / f"{Path(db_name).stem}.xls"

    target_db_path = prj_root / local_data_path / sqlite_db_name

    if not source_excel_path.exists():
        raise FileNotFoundError(f"Excel-Quelldatei nicht gefunden: {source_excel_path}")

    logger.info(f"Importiere Stammdaten von {source_excel_path} nach {target_db_path}")

    total_imported = 0
    report: Dict[str, Dict[str, List[str]]] = {}
    with sqlite3.connect(target_db_path) as target_conn:
        target_conn.execute("PRAGMA foreign_keys = ON")
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
            create_target_tables(
                target_conn,
                entity_name,
                target_table,
                fields,
                foreign_keys=FOREIGN_KEY_MAPPINGS.get(target_table),
            )

            # Daten importieren
            try:
                inserted, updated, deactivated, details = import_entity_data(
                    source_excel=source_excel_path,
                    target_conn=target_conn,
                    excel_table_name=excel_table,
                    target_table=target_table,
                    fields=fields,
                    foreign_keys=FOREIGN_KEY_MAPPINGS.get(target_table),
                )
                total_imported += inserted + updated
                report[entity_name] = details
            except Exception as e:
                logger.error(f"Fehler beim Import von {excel_table}: {e}")

        _write_report(config, report)

    if source_excel_path.parent.resolve() == imports_path.resolve():
        done_dir = ensure_dir(config.get_done_path())
        target_path = done_dir / source_excel_path.name
        shutil.move(str(source_excel_path), str(target_path))
        logger.info(f"Stammdatendatei verschoben nach: {target_path}")

    logger.info(f"Stammdaten-Import abgeschlossen. {total_imported} Datensätze importiert.")
    return total_imported


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized if normalized else None
    return value


def _values_equal(a: Any, b: Any) -> bool:
    na = _normalize_value(a)
    nb = _normalize_value(b)
    if isinstance(na, (int, float)) and isinstance(nb, (int, float)):
        return float(na) == float(nb)
    return na == nb


def _diff_row(existing: Dict[str, Any], incoming: Dict[str, Any], fields: list[FieldConfig]) -> Dict[str, str]:
    changes: Dict[str, str] = {}
    for field in fields:
        if field.primary_key:
            continue
        col = field.name
        if not _values_equal(existing.get(col), incoming.get(col)):
            changes[col] = f"{existing.get(col)} → {incoming.get(col)}"
    return changes


def _pk_key(row: Dict[str, Any], pk_fields: list[str]) -> Optional[Tuple[Any, ...]]:
    if not pk_fields:
        return None
    values = tuple(row.get(pk) for pk in pk_fields)
    if any(v is None or (isinstance(v, str) and v.strip() == "") for v in values):
        return None
    return values


def _format_pk(pk: Tuple[Any, ...]) -> str:
    if len(pk) == 1:
        return str(pk[0])
    return "|".join(str(value) for value in pk)


def _format_changes(changes: Dict[str, str]) -> str:
    if not changes:
        return ""
    parts = [f"{field}: {delta}" for field, delta in changes.items()]
    return f" ({'; '.join(parts)})"


def _pk_where_clause(pk_fields: list[str], pk: Tuple[Any, ...]) -> Tuple[str, Tuple[Any, ...]]:
    clause = " AND ".join([f"{field}=?" for field in pk_fields])
    return clause, pk


def _load_existing_rows(
    conn: sqlite3.Connection, target_table: str, select_cols: list[str], pk_fields: list[str]
) -> List[Dict[str, Any]]:
    sql = f"SELECT {', '.join(select_cols)} FROM {target_table}"
    cur = conn.execute(sql)
    rows = []
    for raw in cur.fetchall():
        row = dict(zip(select_cols, raw))
        key = _pk_key(row, pk_fields)
        if key is not None:
            row["_pk_key"] = key
            rows.append(row)
    return rows


def _write_report(config: Config, report: Dict[str, Dict[str, List[str]]]) -> None:
    if not report:
        return
    log_dir = ensure_dir(Path(config.structure.prj_root) / (config.structure.log_path or ".logs"))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = log_dir / f"stammdaten_import_report_{stamp}.md"

    lines = [
        "# Stammdaten-Import Report",
        "",
        f"Zeitpunkt: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
        "",
    ]

    for entity, details in report.items():
        inserted = details.get("inserted", [])
        updated = details.get("updated", [])
        deactivated = details.get("deactivated", [])

        lines.extend(
            [
                f"## {entity}",
                f"Eingefügt: {len(inserted)}",
                f"Aktualisiert: {len(updated)}",
                f"Deaktiviert: {len(deactivated)}",
                "",
            ]
        )

        if inserted:
            lines.append(f"Eingefügt IDs: {', '.join(f'`{pk}`' for pk in inserted)}")
        if updated:
            lines.append("Aktualisiert: " + "; ".join(updated))
        if deactivated:
            lines.append(f"Deaktiviert IDs: {', '.join(f'`{pk}`' for pk in deactivated)}")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Import-Report geschrieben: {report_path}")


def main() -> None:
    """Hauptfunktion: Liest die Konfiguration und importiert die Stammdaten."""
    config = Config()
    run_import(config)


if __name__ == "__main__":
    main()
