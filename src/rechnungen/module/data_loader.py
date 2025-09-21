from pathlib import Path
from typing import Optional
import pandas as pd
from openpyxl import load_workbook
from module.config import Config
from module.entity import LegalPerson, PrivatePerson
from module.invoice_filter import InvoiceFilter
from loguru import logger  # Zentrales Logging-System


class DataLoader:
    """
    Klasse zum Laden und Prüfen von Daten aus einer Excel-Datenbank.
    Nutzt die Konfiguration für erwartete Spalten und Filter.
    """

    def __init__(self, config: Config, filter: InvoiceFilter):
        """
        Initialisiert den DataLoader mit einer Konfigurationsinstanz.

        Args:
            config (Config): Singleton-Konfiguration mit allen Einstellungen.
            filter (InvoiceFilter): Filterobjekt mit den Filterkriterien.
        """
        self.config = config
        self.filter = filter

    def load_data(
        self,
        db: Path,
        sheet: Optional[str], 
        ) -> pd.DataFrame:
        """
        Lädt die Daten aus einer Excel-Datei und filtert sie nach Leistungszeitraum.

        Args:
            db (Path): Pfad zur Excel-Datenbank.
            sheet (str, optional): Name des Arbeitsblatts. Falls None, wird das aktive Blatt verwendet.
        Returns:
            pd.DataFrame: Gefilterte Daten als DataFrame.
        """
        
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

        # Alle Felder mit "(Leer)" durch "" ersetzen
        df = df.replace("(Leer)", "")

        # IMPORTANT: Dynamische Filterung nach allen gesetzten Feldern im Filterobjekt
        filter_dict = self.filter.__dict__
        for key, value in filter_dict.items():
            if value is None:
                continue
            # Bereichsfilter (z.B. service_date_range)
            if key.endswith("_range") and isinstance(value, tuple) and len(value) == 2:
                col_name = key.replace("_range", "")
                if col_name in df.columns:
                    df = df[df[col_name].between(value[0], value[1])]
            # Listenfilter (z.B. payer_list, client_list)
            elif key.endswith("_list") and isinstance(value, (list, tuple)):
                col_name = key.replace("_list", "")
                if col_name in df.columns:
                    df = df[df[col_name].isin(value)]
            # Einzelwertfilter
            else:
                if key in df.columns:
                    df = df[df[key] == value]

        return df

    def check_data_consistency(self, df: pd.DataFrame):
        """
        Prüft, ob alle erwarteten Spalten im DataFrame vorhanden sind.

        Args:
            df (pd.DataFrame): Zu prüfender DataFrame.

        Raises:
            ValueError: Falls erwartete Spalten fehlen.
        """
        # Extrahiere die erwarteten Spaltennamen aus der segmentierten Konfiguration
        payer_cols = [col["name"] for col in self.config.data["expected_columns"].get("payer", [])]
        client_cols = [col["name"] for col in self.config.data["expected_columns"].get("client", [])]
        general_cols = [col["name"] for col in self.config.data["expected_columns"].get("general", [])]

        expected_columns = set(payer_cols + client_cols + general_cols)
        missing_columns = expected_columns - set(df.columns)
        if missing_columns:
            missing_str = "\n".join(sorted(missing_columns))
            logger.warning(f"Fehlende Spalten: {missing_str}")
            raise ValueError(f"Fehlende Felder in der Pivot-Tabelle: {missing_str}")
        

if __name__ == "__main__":
    print("DataLoader Modul. Nicht direkt ausführbar.")
