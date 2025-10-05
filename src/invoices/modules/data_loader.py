from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger
from openpyxl import load_workbook

from shared_modules.config import Config, ExpectedColumnsConfig
from modules.invoice_filter import InvoiceFilter

class DataLoader:
    """
    Klasse zum Laden und Prüfen von Daten aus einer Excel-Datenbank.
    Nutzt die Pydantic-basierte Konfiguration für erwartete Spalten und Filter.
    """

    def __init__(self, config: Config, filter: InvoiceFilter):
        """
        Initialisiert den DataLoader mit einer Konfigurationsinstanz und einem Filterobjekt.
        Beide werden konsequent als Pydantic-Modelle genutzt.
        Args:
            config (Config): Singleton-Konfiguration mit Pydantic-Modell.
            filter (InvoiceFilter): Pydantic-Modell mit den Filterkriterien.
        """
        self.config: Config = config
        self.filter: InvoiceFilter = filter

    def load_data(
        self,
        db: Path,
        sheet: Optional[str], 
    ) -> pd.DataFrame:
        """
        Lädt die Daten aus einer Excel-Datei und filtert sie nach den Kriterien im Filterobjekt.
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

        # Dynamische Filterung nach allen gesetzten Feldern im Pydantic-Filterobjekt
        for key, value in self.filter.model_dump().items():
            if value is None:
                continue
            # Bereichsfilter (z.B. service_date_range)
            if key.endswith("_range") and isinstance(value, (list, tuple)) and len(value) == 2:
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

    def check_data_consistency(self, df: pd.DataFrame) -> None:
        """
        Prüft, ob alle erwarteten Spalten im DataFrame vorhanden sind.
        Nutzt die Pydantic-basierte Konfiguration für die Spaltendefinitionen.
        Args:
            df (pd.DataFrame): Zu prüfender DataFrame.
        Raises:
            ValueError: Falls erwartete Spalten fehlen.
            TypeError: Falls Summenfelder nicht numerisch sind.
        """
        # Extrahiere die erwarteten Spaltennamen aus der Pydantic-Konfiguration
        expected_columns_model: ExpectedColumnsConfig = self.config.get_expected_columns()
        expected_columns = set()
        for section in ["payer", "client", "general"]:
            # Die Konfiguration liefert jetzt Pydantic-Modelle, daher Zugriff über Attribute
            col_list = getattr(expected_columns_model, section, [])
            expected_columns.update(col.name for col in col_list)
        missing_columns = expected_columns - set(df.columns)
        if missing_columns:
            missing_str = "\n".join(sorted(missing_columns))
            logger.warning(f"Fehlende Spalten: {missing_str}")
            raise ValueError(f"Fehlende Felder in der Pivot-Tabelle: {missing_str}")

        # Prüfe, ob alle Summenfelder numerisch sind
        sum_columns = [
            col.name
            for col in getattr(expected_columns_model, "general", [])
            if getattr(col, "sum", False)
        ]
        for col in sum_columns:
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                logger.warning(f"Summenfeld '{col}' ist nicht numerisch!")
                raise TypeError(f"Summenfeld '{col}' muss numerisch sein, ist aber {df[col].dtype}.")

if __name__ == "__main__":
    print("DataLoader Modul. Nicht direkt ausführbar.")
