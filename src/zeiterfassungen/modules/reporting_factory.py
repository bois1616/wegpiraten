from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from openpyxl import load_workbook
from pydantic import ValidationError
from loguru import logger

from .reporting_factory_config import ReportingFactoryConfig


class ReportingFactory:
    """
    Factory-Klasse zur Erstellung von Reporting-Sheets.
    Erwartet ein Pydantic-Modell für die Konfiguration.
    """

    def __init__(self, config: ReportingFactoryConfig):
        """
        Konstruktor erwartet ein Pydantic-Modell für die Konfiguration.
        Das sorgt für Typsicherheit und Validierung der Konfigurationsdaten.
        Das Passwort für den Blattschutz wird sicher aus der Umgebung geladen.
        """
        from shared_modules.config import Config

        self.config: ReportingFactoryConfig = config
        # sheet_password sicher aus Umgebungsvariable/.env laden, falls nicht gesetzt
        if not self.config.sheet_password:
            # Versuche zuerst entschlüsseltes Secret zu laden
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
        # Zugriff auf Template-Name und Passwort über das Pydantic-Modell
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
            ws["c5"] = header_data["Sozialpädagogin"]
            ws["g5"] = header_data["MA_ID"]
            ws["c6"] = reporting_month_dt
            ws["c6"].number_format = "MM.YYYY"
            ws["c7"] = header_data["Stunden pro Monat"]
            ws["g7"] = header_data["SPF / BBT"]
            ws["c8"] = header_data["Kürzel"]
            ws["g8"] = header_data["KlientNr"]
        except Exception as e:
            logger.error(f"Fehler beim Ausfüllen des Sheets: {e}")
            raise RuntimeError(f"Fehler beim Ausfüllen des Sheets: {e}")

        # Blattschutz nur wieder aktivieren, wenn die Originaldatei geschützt war
        if original_sheet_protected:
            ws.protection.sheet = True
            ws.protection.enable()
            # sheet_password-Argument hat Vorrang, sonst Konfiguration
            password = sheet_password if sheet_password is not None else self.config.sheet_password
            if password is None:
                logger.error("Sheet-Passwort ist nicht gesetzt!")
                raise RuntimeError("Sheet-Passwort ist nicht gesetzt!")
            ws.protection.set_password(str(password))
            ws.protection.objects = True  # <--- Diese Zeile ergänzt den Objektschutz
            # Die folgenden Attribute sind optional und nicht in allen openpyxl-Versionen verfügbar
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
        dateiname: str = f"{header_data['KlientNr']} ({header_data['Kürzel']})_{reporting_month_dt.strftime('%Y-%m')}.xlsx"
        try:
            wb.save(output_path / dateiname)
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Datei: {e}")
            raise RuntimeError(f"Fehler beim Speichern der Datei: {e}")
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
