from datetime import datetime
from pathlib import Path
from typing import Any, List
import pandas as pd
import sqlite3
from loguru import logger

from shared_modules.config import Config
from zeiterfassungen.modules.reporting_factory import ReportingFactory
from zeiterfassungen.modules.reporting_row_model import ReportingRowModel


class ReportingProcessor:
    """
    Klasse zur Verarbeitung von Reporting-Daten.
    Nutzt ausschließlich Pydantic-Modelle für Konfiguration und Daten.
    Holt die Daten aus der SQLite-Datenbank gemäß zentraler Config.
    """

    def __init__(self, config: Config, reporting_factory: ReportingFactory):
        """
        Konstruktor erwartet das zentrale Config-Objekt und eine Factory für die Sheet-Erstellung.
        Die Konfiguration wird einmal geprüft und dann als vertrauenswürdig angenommen.
        """
        self.config: Config = config
        self.reporting_factory: ReportingFactory = reporting_factory

        # Prüfe, ob alle relevanten Pfade und Einstellungen vorhanden sind
        assert self.config.structure.prj_root, "Projektwurzel fehlt in der Config!"
        assert self.config.database.sqlite_db_name, "Datenbankname fehlt in der Config!"
        assert self.config.templates.reporting_template, "Reporting-Template fehlt in der Config!"

    def get_sheet_password(self) -> str:
        """
        Holt das Excel-Blattschutz-Passwort sicher aus der Umgebung (.env), entschlüsselt falls nötig.
        Gibt SHEET_PASSWORD_ENC (verschlüsselt) oder SHEET_PASSWORD (Klartext) zurück.

        Returns:
            str: Das entschlüsselte oder im Klartext gespeicherte Passwort.

        Raises:
            RuntimeError: Wenn kein Passwort gefunden werden kann.
        """
        pw = self.config.get_decrypted_secret("SHEET_PASSWORD_ENC")
        if not pw:
            pw = self.config.get_secret("SHEET_PASSWORD")
        if not pw:
            logger.error(
                "Excel-Blattschutz-Passwort nicht gesetzt! Bitte .env mit SHEET_PASSWORD_ENC oder SHEET_PASSWORD anlegen."
            )
            raise RuntimeError(
                "Excel-Blattschutz-Passwort nicht gesetzt! Bitte .env mit SHEET_PASSWORD_ENC oder SHEET_PASSWORD anlegen."
            )
        return pw

    def load_client_data(self, reporting_month: str) -> List[ReportingRowModel]:
        """
        Lädt die Klientendaten für den angegebenen Berichtsmonat aus der SQLite-DB.
        Nutzt die validierte Pydantic-Konfiguration für alle Pfadangaben und dynamische Modelle.

        Args:
            reporting_month (str): Monat im Format "YYYY-MM".

        Returns:
            List[ReportingRowModel]: Gefilterte und validierte Klientendaten.
        """
        # Pfade aus der Config
        prj_root = Path(self.config.structure.prj_root)
        db_name = self.config.database.sqlite_db_name
        db_path = prj_root / "data" / db_name

        # SQL: Hole alle aktiven Clients im Berichtsmonat, ergänze Mitarbeiterdaten
        month_start = f"{reporting_month}-01"
        sql = """
        SELECT
            c.client_id,
            c.short_code,
            c.allowed_hours_per_month,
            c.employee_id,
            c.first_name AS client_first_name,
            c.last_name AS client_last_name,
            c.service_type,
            e.first_name AS employee_first_name,
            e.last_name AS employee_last_name
        FROM clients c
        LEFT JOIN employees e ON c.employee_id = e.emp_id
        WHERE (c.end_date IS NULL OR c.end_date >= ?)
        """
        logger.info(f"Führe Client-Query für Monat {reporting_month} aus.")
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(sql, conn, params=(month_start,))
        logger.info(f"{len(df)} Klientendatensätze geladen.")

        # Validierung und Typisierung mit Pydantic
        reporting_rows: List[ReportingRowModel] = []
        for idx, row in df.iterrows():
            try:
                reporting_row = ReportingRowModel(**row.to_dict())
                reporting_rows.append(reporting_row)
            except Exception as e:
                logger.error(f"Ungültige Reporting-Daten in Zeile {idx}: {e}")
        return reporting_rows

    def run(self, reporting_month: str, output_path: Path, template_path: Path) -> None:
        """
        Führt die Berichtsverarbeitung für den angegebenen Monat aus.

        Args:
            reporting_month (str): Monat im Format "YYYY-MM".
            output_path (Path): Zielverzeichnis für die erzeugten Dateien.
            template_path (Path): Verzeichnis mit den Excel-Templates.
        """
        reporting_month_dt = datetime.strptime(reporting_month, "%Y-%m")
        reporting_rows = self.load_client_data(reporting_month)
        sheet_password = self.get_sheet_password()
        for header_data in reporting_rows:
            try:
                dateiname = self.reporting_factory.create_reporting_sheet(
                    header_data=header_data,
                    reporting_month_dt=reporting_month_dt,
                    output_path=output_path,
                    template_path=template_path,
                    sheet_password=sheet_password,
                )
                logger.info(
                    f"Erstelle AZ Erfassungsbogen für {header_data.employee_first_name} "
                    f"({header_data.short_code}, Client-ID: {header_data.client_id}) -> {dateiname}"
                )
            except Exception as e:
                logger.error(f"Fehler beim Erstellen des Sheets für Client {header_data.client_id}: {e}")

# Vorschläge für weitere Modelle:
# - Ein Modell für die Reporting-Konfiguration (z.B. ReportingConfig), das alle relevanten Einstellungen für die Berichtsverarbeitung kapselt.
# - Ein Modell für die Sheet-Templates, falls mehrere Vorlagen unterstützt werden sollen.
# - Ein Modell für die Ausgabe- und Speicherstruktur (z.B. OutputConfig), um Pfade und Dateinamen zentral zu verwalten.

# Beispiel für die Initialisierung mit zentralem Config-Objekt
if __name__ == "__main__":
    config_path = Path(__file__).parent.parent.parent.parent / ".config" / "wegpiraten_config.yaml"
    config = Config(config_path)
    factory = ReportingFactory(config)
    processor = ReportingProcessor(config, factory)
    db_path = Path(config.structure.prj_root) / config.structure.local_data_path / config.database.sqlite_db_name
    output_path = Path(config.structure.prj_root) / config.structure.output_path
    template_path = Path(config.structure.prj_root) / config.structure.template_path
    processor.run("2025-08", output_path, template_path)
