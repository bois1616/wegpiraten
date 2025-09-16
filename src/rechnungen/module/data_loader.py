from pathlib import Path
from typing import Optional
import pandas as pd
from openpyxl import load_workbook
from module.config import Config
from loguru import logger  # Zentrales Logging-System


class DataLoader:
    """
    Klasse zum Laden und Prüfen von Daten aus einer Excel-Datenbank.
    Nutzt die Konfiguration für erwartete Spalten und Filter.
    """

    def __init__(self, config: Config):
        """
        Initialisiert den DataLoader mit einer Konfigurationsinstanz.

        Args:
            config (Config): Singleton-Konfiguration mit allen Einstellungen.
        """
        self.config = config

    def load_data(
        self,
        db: Path,
        sheet: Optional[str],
        start_inv_period: Optional[str],
        end_inv_period: Optional[str],
    ) -> pd.DataFrame:
        """
        Lädt die Daten aus einer Excel-Datei und filtert sie nach Leistungszeitraum.

        Args:
            db (Path): Pfad zur Excel-Datenbank.
            sheet (str, optional): Name des Arbeitsblatts. Falls None, wird das aktive Blatt verwendet.
            start_inv_period (str, optional): Startdatum Leistungszeitraum ('YYYY-MM-DD').
            end_inv_period (str, optional): Enddatum Leistungszeitraum ('YYYY-MM-DD').

        Returns:
            pd.DataFrame: Gefilterte Daten als DataFrame.
        """
        # Annahme: start_inv_period und end_inv_period wurden bereits außerhalb geprüft und konvertiert ("check once and then trust")
        work_book = load_workbook(db, data_only=True)
        work_sheet = work_book[sheet] if sheet else work_book.active

        # Die ersten drei Zeilen sind Metadaten und werden übersprungen
        data = work_sheet.values
        for _ in range(3):
            next(data)
        # Die vierte Zeile enthält die Spaltennamen (ohne die erste Spalte)
        columns = next(data)[1:]
        # Die eigentlichen Daten ab der zweiten Spalte
        df = pd.DataFrame((row[1:] for row in data), columns=columns)

        # Aufwandsdaten auf den gewählten Leistungszeitraum begrenzen
        start_date = pd.to_datetime(start_inv_period)
        end_date = pd.to_datetime(end_inv_period)
        df = df[
            (df["Leistungsdatum"] >= start_date) & (df["Leistungsdatum"] <= end_date)
        ]

        # Fehlende Werte in ZD_Name2 mit Leerzeichen auffüllen/ersetzen
        if "ZD_Name2" in df.columns:
            df["ZD_Name2"] = df["ZD_Name2"].fillna("").replace("(Leer)", "")
        logger.info("Daten erfolgreich geladen und gefiltert.")
        return df

    def check_data_consistency(self, df: pd.DataFrame):
        """
        Prüft, ob alle erwarteten Spalten im DataFrame vorhanden sind.

        Args:
            df (pd.DataFrame): Zu prüfender DataFrame.

        Raises:
            ValueError: Falls erwartete Spalten fehlen.
        """
        # Extrahiere die erwarteten Spaltennamen aus der Konfiguration
        expected_columns = {
            col["name"] if isinstance(col, dict) else col
            for col in self.config.data["expected_columns"]
        }
        missing_columns = expected_columns - set(df.columns)
        if missing_columns:
            missing_str = "\n".join(sorted(missing_columns))
            logger.warning(f"Fehlende Spalten: {missing_str}")
            raise ValueError(f"Fehlende Felder in der Pivot-Tabelle: {missing_str}")
        logger.info("Alle erwarteten Spalten sind vorhanden.")
    
# if __name__ == "__main__":
#     print("DataLoader Modul. Nicht direkt ausführbar.")
