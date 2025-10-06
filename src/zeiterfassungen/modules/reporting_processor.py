from datetime import datetime
from pathlib import Path
from typing import Any
import pandas as pd
from loguru import logger

from shared_modules.config import Config
from .reporting_config import ReportingConfig
from .reporting_factory import ReportingFactory

import sqlite3


class ReportingProcessor:
    """
    Klasse zur Verarbeitung von Reporting-Daten.
    Erwartet ausschließlich Pydantic-Modelle für Konfiguration und nutzt Typsicherheit.
    Holt die Daten jetzt aus der SQLite-Datenbank gemäß zentraler Config.
    """

    def get_sheet_password(self) -> str:
        """
        Holt das Excel-Blattschutz-Passwort sicher aus der Umgebung (.env), entschlüsselt falls nötig.
        Gibt SHEET_PASSWORD_ENC (verschlüsselt) oder SHEET_PASSWORD (Klartext) zurück.

        Returns:
            str: Das entschlüsselte oder im Klartext gespeicherte Passwort.

        Raises:
            RuntimeError: Wenn kein Passwort gefunden werden kann.
        """
        config = Config()
        pw = config.get_decrypted_secret("SHEET_PASSWORD_ENC")
        if not pw:
            pw = config.get_secret("SHEET_PASSWORD")
        if not pw:
            logger.error(
                "Excel-Blattschutz-Passwort nicht gesetzt! Bitte .env mit SHEET_PASSWORD_ENC oder SHEET_PASSWORD anlegen."
            )
            raise RuntimeError(
                "Excel-Blattschutz-Passwort nicht gesetzt! Bitte .env mit SHEET_PASSWORD_ENC oder SHEET_PASSWORD anlegen."
            )
        return pw

    def __init__(
        self, reporting_config: ReportingConfig, reporting_factory: ReportingFactory
    ):
        """
        Konstruktor erwartet ein Pydantic-Modell für die Konfiguration.
        Das sorgt für Typsicherheit und Validierung der Konfigurationsdaten.
        """
        self.reporting_config: ReportingConfig = reporting_config
        self.reporting_factory = reporting_factory

    def load_client_data(self, reporting_month: str) -> pd.DataFrame:
        """
        Lädt die Klientendaten für den angegebenen Berichtsmonat aus der SQLite-DB.
        Nutzt die validierte Pydantic-Konfiguration für alle Pfadangaben und dynamische Modelle.

        Args:
            reporting_month (str): Monat im Format "YYYY-MM".

        Returns:
            pd.DataFrame: Gefilterte Klientendaten.
        """
        # Zugriff auf die SQLite-DB und Tabellenname aus der Config
        config = Config()
        prj_root = Path(config.data.structure.prj_root)
        local_data_path = Path(config.data.structure.local_data_path)
        db_name = config.data.database.sqlite_db_name
        db_path = prj_root / local_data_path / db_name

        # Ziel-Tabelle (Clients) aus table_mappings bestimmen
        table_mappings = config.data.table_mappings
        client_table = table_mappings["MD_Client"]["target"]

        # SQL-Join: Clients + Employees + Payer + ServiceRequester + InvoiceData
        sql = f"""
        SELECT
            c.client_id,
            c.first_name,
            c.last_name,
            c.short_code,
            c.allowed_hours_per_month,
            c.employee_id,
            c.start_date,
            c.end_date,
            c.service_type,
            c.notes,
            e.first_name AS employee_first_name,
            e.last_name AS employee_last_name,
            e.fte,
            e.notes AS employee_notes,
            p.name AS payer_name,
            s.name AS service_requester_name
        FROM {client_table} c
        LEFT JOIN employees e ON c.employee_id = e.emp_id
        LEFT JOIN payer p ON c.payer_id = p.payer_id
        LEFT JOIN service_requester s ON c.service_requester_id = s.service_requester_id
        WHERE
            (c.end_date IS NULL OR c.end_date >= ?)
        """
        reporting_month_dt = datetime.strptime(reporting_month, "%Y-%m")
        logger.info(f"Führe Client-Join-Query für Monat {reporting_month} aus: {sql}")

        with sqlite3.connect(db_path) as conn:
            client_masterdata = pd.read_sql_query(sql, conn, params=(reporting_month_dt.strftime("%Y-%m-%d"),))

        logger.info(f"{len(client_masterdata)} Klientendatensätze geladen.")
        return client_masterdata

    def run(self, reporting_month: str, output_path: Path, template_path: Path) -> None:
        """
        Führt die Berichtsverarbeitung für den angegebenen Monat aus.

        Args:
            reporting_month (str): Monat im Format "YYYY-MM".
            output_path (Path): Zielverzeichnis für die erzeugten Dateien.
            template_path (Path): Verzeichnis mit den Excel-Templates.
        """
        reporting_month_dt = datetime.strptime(reporting_month, "%Y-%m")
        client_masterdata = self.load_client_data(reporting_month)
        sheet_password = self.get_sheet_password()
        for _, header_data in client_masterdata.iterrows():
            dateiname = self.reporting_factory.create_reporting_sheet(
                header_data=header_data,
                reporting_month_dt=reporting_month_dt,
                output_path=output_path,
                template_path=template_path,
                sheet_password=sheet_password,
            )
            logger.info(
                f"Erstelle AZ Erfassungsbogen für {header_data.get('employee_first_name', '')} "
                f"({header_data.get('short_code', '')}, Ende: {header_data.get('end_date', '')}) -> {dateiname}"
            )


# Beispiel für die Initialisierung mit Pydantic
if __name__ == "__main__":
    import yaml
    from pydantic import ValidationError

    config_path = Path("wegpiraten_reporting_config.yaml")
    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)
    try:
        config = ReportingConfig(**raw_config)
    except ValidationError as e:
        print(f"Konfigurationsfehler: {e}")
        exit(1)

    # Factory-Objekt muss bereitgestellt werden
    factory = None  # Platzhalter
    processor = ReportingProcessor(config, factory)
    # processor.run("2025-08", Path("output"), Path("template.xlsx"))
