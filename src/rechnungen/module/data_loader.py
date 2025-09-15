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

    def load_data(self, db: Path, sheet: Optional[str], abrechnungsmonat: Optional[pd.Timestamp | str]) -> pd.DataFrame:
        """
        Lädt die Daten aus einer Excel-Datei und filtert sie nach dem Abrechnungsmonat.

        Args:
            db (Path): Pfad zur Excel-Datenbank.
            sheet (str, optional): Name des Arbeitsblatts. Falls None, wird das aktive Blatt verwendet.
            abrechnungsmonat (pd.Timestamp | str, optional): Abrechnungsmonat als Timestamp oder 'YYYY-MM'-String.

        Returns:
            pd.DataFrame: Gefilterte Daten als DataFrame.

        Raises:
            ValueError: Falls der Abrechnungsmonat nicht korrekt übergeben wird.
        """
        work_book = load_workbook(db, data_only=True)
        work_sheet = work_book[sheet] if sheet else work_book.active

        # Abrechnungsmonat als Timestamp bestimmen
        if abrechnungsmonat is None:
            abrechnungsmonat = pd.Timestamp.now().to_period("M").to_timestamp()
        elif isinstance(abrechnungsmonat, str):
            abrechnungsmonat = pd.to_datetime(abrechnungsmonat, format="%Y-%m")
        elif not isinstance(abrechnungsmonat, pd.Timestamp):
            logger.error("Abrechnungsmonat muss ein String im Format 'YYYY-MM' oder ein pd.Timestamp sein")
            raise ValueError("abrechnungsmonat muss ein String im Format 'YYYY-MM' oder ein pd.Timestamp sein")

        # Die ersten drei Zeilen sind Metadaten und werden übersprungen
        data = work_sheet.values
        for _ in range(3):
            next(data)
        # Die vierte Zeile enthält die Spaltennamen (ohne die erste Spalte)
        columns = next(data)[1:]
        # Die eigentlichen Daten ab der zweiten Spalte
        df = pd.DataFrame((row[1:] for row in data), columns=columns)

        # Filter auf den Abrechnungsmonat anwenden
        monat_start: pd.Timestamp = abrechnungsmonat
        monat_ende: pd.Timestamp = abrechnungsmonat + pd.offsets.MonthEnd(0)
        df = df[(df["Leistungsdatum"] >= monat_start) & (df["Leistungsdatum"] <= monat_ende)]

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
        expected_columns = {col["name"] if isinstance(col, dict) else col for col in self.config.data["expected_columns"]}
        missing_columns = expected_columns - set(df.columns)
        if missing_columns:
            missing_str = "\n".join(sorted(missing_columns))
            logger.warning(f"Fehlende Spalten: {missing_str}")
            raise ValueError(f"Fehlende Felder in der Pivot-Tabelle: {missing_str}")
        logger.info("Alle erwarteten Spalten sind vorhanden.")
