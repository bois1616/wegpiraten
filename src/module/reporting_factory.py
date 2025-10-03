from pathlib import Path
from datetime import datetime
import pandas as pd
from openpyxl import load_workbook
from pydantic import BaseModel,  ValidationError


class ReportingFactoryConfig(BaseModel):
    """
    Pydantic-Modell für die Konfiguration der ReportingFactory.
    Sorgt für Typsicherheit und Validierung der Konfigurationsdaten.
    """
    reporting_template: str = "zeiterfassunsboegen.xlsx"  # Standard-Template-Dateiname
    sheet_password: str = "wegpiraten"                   # Standard-Passwort für Blattschutz

class ReportingFactory:
    """
    Factory-Klasse zur Erstellung von Reporting-Sheets.
    Erwartet ein Pydantic-Modell für die Konfiguration.
    """
    def __init__(self, config: ReportingFactoryConfig):
        """
        Konstruktor erwartet ein Pydantic-Modell für die Konfiguration.
        Das sorgt für Typsicherheit und Validierung der Konfigurationsdaten.
        """
        self.config: ReportingFactoryConfig = config

    def create_reporting_sheet(
        self,
        row: pd.Series,
        reporting_month_dt: datetime,
        output_path: Path,
        template_path: Path
    ) -> str:
        """
        Erstellt ein Reporting-Sheet auf Basis der übergebenen Datenreihe und speichert es ab.
        Alle Konfigurationswerte werden typisiert über das Pydantic-Modell bezogen.

        Args:
            row (pd.Series): Datenzeile mit den auszufüllenden Werten.
            reporting_month_dt (datetime): Berichtsmonat als Datum.
            output_path (Path): Zielverzeichnis für das Reporting-Sheet.
            template_path (Path): Verzeichnis mit dem Excel-Template.

        Returns:
            str: Dateiname der erzeugten Excel-Datei.
        """
        # Zugriff auf Template-Name und Passwort über das Pydantic-Modell
        template_name: str = self.config.reporting_template
        wb = load_workbook(template_path / template_name)
        ws = wb.active

        # Blattschutz deaktivieren, um Felder zu beschreiben
        ws.protection.sheet = False

        # Ausfüllen der relevanten Felder im Excel-Sheet
        ws["c5"] = row["Sozialpädagogin"]
        ws["g5"] = row["MA_ID"]
        ws["c6"] = reporting_month_dt
        ws["c6"].number_format = "MM.YYYY"
        ws["c7"] = row["Stunden pro Monat"]
        ws["g7"] = row["SPF / BBT"]
        ws["c8"] = row["Kürzel"]
        ws["g8"] = row["KlientNr"]

        # Blattschutz wieder aktivieren und mit Passwort versehen
        ws.protection.sheet = True
        ws.protection.enable()
        ws.protection.set_password(self.config.sheet_password)
        ws.protection.enable_select_locked_cells = False
        ws.protection.enable_select_unlocked_cells = True
        ws.protection.format_cells = False
        ws.protection.format_columns = False
        ws.protection.format_rows = False
        ws.protection.insert_columns = False
        ws.protection.insert_rows = False
        ws.protection.insert_hyperlinks = False
        ws.protection.delete_columns = False
        ws.protection.delete_rows = False
        ws.protection.sort = False
        ws.protection.auto_filter = False
        ws.protection.objects = False
        ws.protection.scenarios = False

        # Dateinamen generieren und Datei speichern
        dateiname: str = f"Aufwandserfassung_{reporting_month_dt.strftime('%Y-%m')}_{row['Kürzel']}.xlsx"
        wb.save(output_path / dateiname)
        return dateiname

# Beispiel für die Initialisierung mit Pydantic
if __name__ == "__main__":
    import yaml

    # Beispiel: YAML-Konfiguration laden und mit Pydantic validieren
    config_path = Path("wegpiraten_reporting_factory_config.yaml")
    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)
    try:
        config = ReportingFactoryConfig(**raw_config)
    except ValidationError as e:
        print(f"Konfigurationsfehler: {e}")
        exit(1)

    # Beispielhafte Nutzung
    factory = ReportingFactory(config)
    # Hier müssten row, reporting_month_dt, output_path, template_path übergeben werden
    # factory.create_reporting_sheet(row, reporting_month_dt, output_path, template_path)