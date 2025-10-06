from datetime import datetime
from pathlib import Path
from typing import Optional
import sqlite3
import pandas as pd
from openpyxl import load_workbook
from pydantic import ValidationError
from loguru import logger

from .reporting_factory_config import ReportingFactoryConfig
from shared_modules.config import Config


class ReportingFactory:
    """
    Factory-Klasse zur Erstellung von Reporting-Sheets.
    Erwartet ein Pydantic-Modell für die Konfiguration.
    Holt die Daten jetzt aus der SQLite-Datenbank gemäß zentraler Config.
    """

    def __init__(self, config: ReportingFactoryConfig):
        """
        Konstruktor erwartet ein Pydantic-Modell für die Konfiguration.
        Das Passwort für den Blattschutz wird sicher aus der Umgebung geladen.
        """
        self.config: ReportingFactoryConfig = config
        # sheet_password sicher aus Umgebungsvariable/.env laden, falls nicht gesetzt
        if not self.config.sheet_password:
            secret = Config().get_decrypted_secret("SHEET_PASSWORD_ENC")
            if not secret:
                # Fallback: Unverschlüsseltes Secret
                secret = Config().get_secret("SHEET_PASSWORD")
            if not secret:
                logger.error("SHEET_PASSWORD_ENC oder SHEET_PASSWORD nicht gesetzt!\nBitte .env anlegen und Passwort eintragen.")
                raise RuntimeError(
                    "SHEET_PASSWORD_ENC oder SHEET_PASSWORD nicht gesetzt!\nBitte .env anlegen und Passwort eintragen."
                )
            self.config.sheet_password = secret

    def get_db_connection(self, db_path: Path) -> sqlite3.Connection:
        """Öffnet eine SQLite-Verbindung zur angegebenen Datei."""
        logger.info(f"Öffne SQLite-DB: {db_path}")
        return sqlite3.connect(db_path)

    def fetch_reporting_data(
        self, db_path: Path, reporting_month: str
    ) -> pd.DataFrame:
        """
        Holt alle für das Reporting benötigten Daten aus der SQLite-DB.
        Erstellt die erforderlichen Joins und filtert auf den gewünschten Monat.
        """
        # Hole Tabellen- und Feldnamen aus der zentralen Config
        config = Config()
        table_mappings = config.data.table_mappings
        models = config.data.models

        
        sql = f"""
        SELECT
            i.invoice_number,
            i.client_id,
            c.first_name AS client_first_name,
            c.last_name AS client_last_name,
            c.short_code,
            c.allowed_hours_per_month,
            c.employee_id,
            e.first_name AS employee_first_name,
            e.last_name AS employee_last_name,
            i.service_date,
            i.service_type,
            i.travel_time,
            i.direct_time,
            i.indirect_time,
            i.billable_hours,
            i.hourly_rate,
            i.total_hours,
            i.total_costs,
            i.service_requester_name,
            i.payer_id,
            p.name AS payer_name,
            s.name AS service_requester_name
        FROM invoice_data i
        LEFT JOIN clients c ON i.client_id = c.client_id
        LEFT JOIN employees e ON c.employee_id = e.emp_id
        LEFT JOIN payer p ON i.payer_id = p.payer_id
        LEFT JOIN service_requester s ON i.service_requester_name = s.name
        WHERE strftime('%Y-%m', i.service_date) = ?
        """
        logger.info(f"Führe Reporting-Join-Query für Monat {reporting_month} aus.")
        with self.get_db_connection(db_path) as conn:
            df = pd.read_sql_query(sql, conn, params=(reporting_month,))
        logger.info(f"{len(df)} Datensätze für das Reporting geladen.")
        return df

    def create_reporting_sheet(
        self,
        header_data: pd.Series,
        reporting_month_dt: datetime,
        output_path: Path,
        template_path: Path,
        sheet_password: Optional[str] = None,
    ) -> str:
        """
        Erstellt ein Reporting-Sheet auf Basis der übergebenen Datenreihe und speichert es ab.
        Alle Konfigurationswerte werden typisiert über das Pydantic-Modell bezogen.

        Args:
            header_data (pd.Series): Datenzeile mit den auszufüllenden Werten.
            reporting_month_dt (datetime): Berichtsmonat als Datum.
            output_path (Path): Zielverzeichnis für das Reporting-Sheet.
            template_path (Path): Verzeichnis mit dem Excel-Template.

        Returns:
            str: Dateiname der erzeugten Excel-Datei.
        """
        template_name: str = self.config.reporting_template

        try:
            wb = load_workbook(template_path / template_name)
        except Exception as e:
            logger.error(f"Fehler beim Laden des Templates: {e}")
            raise RuntimeError(f"Fehler beim Laden des Templates: {e}")

        ws = wb.active
        if ws is None:
            logger.error("Kein aktives Arbeitsblatt im Template gefunden.")
            raise RuntimeError("Kein aktives Arbeitsblatt im Template gefunden.")

        # Blattschutz deaktivieren, um Felder zu beschreiben
        original_sheet_protected = False
        if hasattr(ws, "protection") and ws.protection and ws.protection.sheet:
            original_sheet_protected = True
            ws.protection.sheet = False

        # Ausfüllen der relevanten Felder im Excel-Sheet
        try:
            ws["c5"] = header_data.get("employee_first_name", "") + " " + header_data.get("employee_last_name", "")
            ws["g5"] = header_data.get("employee_id", "")
            ws["c6"] = reporting_month_dt
            ws["c6"].number_format = "MM.YYYY"
            ws["c7"] = header_data.get("allowed_hours_per_month", "")
            ws["g7"] = header_data.get("service_type", "")
            ws["c8"] = header_data.get("short_code", "")
            ws["g8"] = header_data.get("client_id", "")
        except Exception as e:
            logger.error(f"Fehler beim Ausfüllen des Sheets: {e}")
            raise RuntimeError(f"Fehler beim Ausfüllen des Sheets: {e}")

        # Blattschutz nur wieder aktivieren, wenn die Originaldatei geschützt war
        if original_sheet_protected:
            ws.protection.sheet = True
            ws.protection.enable()
            password = sheet_password if sheet_password is not None else self.config.sheet_password
            if password is None:
                logger.error("Sheet-Passwort ist nicht gesetzt!")
                raise RuntimeError("Sheet-Passwort ist nicht gesetzt!")
            ws.protection.set_password(str(password))
            ws.protection.objects = True
            for attr, value in [
                ("enable_select_locked_cells", False),
                ("enable_select_unlocked_cells", True),
                ("format_cells", False),
                ("format_columns", False),
                ("format_rows", False),
                ("insert_columns", False),
                ("insert_rows", False),
                ("insert_hyperlinks", False),
                ("delete_columns", False),
                ("delete_rows", False),
                ("sort", False),
                ("auto_filter", False),
                ("objects", False),
                ("scenarios", False),
            ]:
                if hasattr(ws.protection, attr):
                    setattr(ws.protection, attr, value)

        # Dateinamen generieren und Datei speichern
        dateiname: str = f"{header_data.get('client_id', '')} ({header_data.get('short_code', '')})_{reporting_month_dt.strftime('%Y-%m')}.xlsx"
        try:
            wb.save(output_path / dateiname)
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Datei: {e}")
            raise RuntimeError(f"Fehler beim Speichern der Datei: {e}")
        return dateiname


# Beispiel für die Initialisierung mit Pydantic
if __name__ == "__main__":
    import yaml

    config_path = Path("wegpiraten_reporting_factory_config.yaml")
    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)
    try:
        config = ReportingFactoryConfig(**raw_config)
    except ValidationError as e:
        print(f"Konfigurationsfehler: {e}")
        exit(1)

    factory = ReportingFactory(config)
    # Beispiel für das Laden der Daten aus der SQLite-DB:
    db_path = Path("Wegpiraten Datenbank.sqlite3")
    reporting_month = "2025-10"
    df = factory.fetch_reporting_data(db_path, reporting_month)
    print(df.head())
