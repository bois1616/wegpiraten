"""
Importiert Stammdaten aus einer bestehenden SQLite-Datenbank (z.B. Excel-Export) in die Projekt-SQLite-DB.
Die Ziel-DB wird automatisch im data-Verzeichnis unterhalb des Projekt-Roots angelegt (Pfad und Name aus Config).
Verwendet zentrale Config, Entity-Modelle aus shared_modules.entity_config und Feld-Mappings aus md_mappings.
"""

from pathlib import Path
import sqlite3
from typing import Dict, Type, Any
import pandas as pd
from loguru import logger

from shared_modules.config import Config
from shared_modules.entity_config import Employee, Client, Payer, ServiceRequester
import md_mappings  # Muss ein Dict mit Tabellen-Mappings bereitstellen

# Mapping: Quell-Tabellenname -> Ziel-Tabellenname und Entity-Modell
TABLES: Dict[str, Dict[str, Any]] = {
    "MD_MA": {"target": "employees", "model": Employee, "mapping": md_mappings.EMPLOYEE_MAPPING},
    "Leistungsbesteller": {"target": "service_requester", "model": ServiceRequester, "mapping": md_mappings.SERVICE_REQUESTER_MAPPING},
    "Zahlungsdienstleister": {"target": "payer", "model": Payer, "mapping": md_mappings.PAYER_MAPPING},
    "MD_Client": {"target": "clients", "model": Client, "mapping": md_mappings.CLIENT_MAPPING},
}

def create_target_tables(conn: sqlite3.Connection) -> None:
    """
    Legt die Zieltabellen in der SQLite-DB an.
    Die Struktur orientiert sich an den Entity-Modellen und verwendet die korrekten Schlüssel.
    """
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            PersNr TEXT PRIMARY KEY,
            Name TEXT,
            Vorname TEXT,
            Nachname TEXT,
            FTE REAL,
            Kommentar TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS service_requester (
            LBNr TEXT PRIMARY KEY,
            Name TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payer (
            ZdNr TEXT PRIMARY KEY,
            Name TEXT,
            Name2 TEXT,
            Strasse TEXT,
            PLZ TEXT,
            Ort TEXT,
            Kommentar TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            KlientNr TEXT PRIMARY KEY,
            Vorname TEXT,
            Nachname TEXT,
            payer_id TEXT,
            service_requester_id TEXT,
            Kommentar TEXT
        )
    """)
    conn.commit()

def map_row(row: pd.Series, mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Mappt die Felder einer Zeile gemäß dem Mapping-Dict.
    """
    return {target: row.get(source) for source, target in mapping.items()}

def import_table(
    source_excel: Path,
    target_conn: sqlite3.Connection,
    source_sheet: str,
    target_table: str,
    model: Type,
    mapping: Dict[str, str],
) -> None:
    """
    Liest alle Daten aus dem angegebenen Excel-Sheet, mappt die Felder und schreibt sie in die Zieltabelle.
    Nutzt das zentrale Entity-Modell zur Validierung.
    """
    logger.info(f"Importiere Sheet {source_sheet} → {target_table}")
    try:
        df = pd.read_excel(source_excel, sheet_name=source_sheet)
    except Exception as e:
        logger.error(f"Fehler beim Lesen von Sheet {source_sheet}: {e}")
        return

    records = []
    for _, row in df.iterrows():
        try:
            mapped = map_row(row, mapping)
            rec = model(**mapped)
            records.append(rec.dict())
        except Exception as e:
            logger.error(f"Fehler beim Validieren eines Datensatzes aus {source_sheet}: {e}")

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
    config_path = Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"
    config = Config()
    config.load(config_path)

    # Ermittle Ziel-DB-Pfad aus der Config
    prj_root = Path(config.get_structure().prj_root)
    data_dir = config.get_structure().data or 'data'
    sqlite_db_name = config.get("sqlite_db_name")
    target_db_path = prj_root / data_dir / sqlite_db_name
    target_db_path.parent.mkdir(parents=True, exist_ok=True)

    # Quelle: aus data_path und db_name
    import_path = Path(config.get_structure().data_path)
    source_db_name = config.get("db_name")
    source_db_path = import_path / source_db_name

    logger.info(f"Quelle: {source_db_path}")
    logger.info(f"Ziel:   {target_db_path}")

    if not source_db_path.exists():
        logger.error(f"Quelldatenbank nicht gefunden: {source_db_path}")
        return

    with sqlite3.connect(source_db_path) as source_conn, \
         sqlite3.connect(target_db_path) as target_conn:
        create_target_tables(target_conn)
        for source_table, meta in TABLES.items():
            try:
                import_table(
                    source_conn,
                    target_conn,
                    source_table,
                    meta["target"],
                    meta["model"],
                    meta["mapping"],
                )
            except Exception as e:
                logger.error(f"Fehler beim Import von {source_table}: {e}")
    logger.info("Stammdaten-Import abgeschlossen.")

if __name__ == "__main__":
    main()