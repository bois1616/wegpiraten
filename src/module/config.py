import yaml
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Any, Optional

# Pydantic-Modell für den Struktur-Teil der Konfiguration
class StructureConfig(BaseModel):
    prj_root: str  # Projektwurzelverzeichnis
    logs: str      # Verzeichnis für Logs

# Pydantic-Modell für die gesamte Konfiguration
class ConfigData(BaseModel):
    locale: str = "de_CH"                       # Gebietsschema
    currency: str = "CHF"                       # Währung
    currency_format: str = "¤#,##0.00"          # Format für Währungsangaben
    date_format: str = "dd.MM.yyyy"             # Datumsformat
    numeric_format: str = "#,##0.00"            # Zahlenformat
    expected_columns: Dict[str, Any] = Field(default_factory=dict)  # Erwartete Spalten (z.B. für Rechnungen)
    structure: StructureConfig                  # Struktur-Teil (siehe oben)

class Config:
    """
    Singleton-Klasse für das Laden und Bereitstellen der Konfiguration.
    Nutzt Pydantic zur Validierung und Typisierung.
    """

    _instance = None  # Statische Variable für die Singleton-Instanz

    def __new__(cls):
        # Singleton-Pattern: Nur eine Instanz pro Prozess
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config: Optional[ConfigData] = None
        return cls._instance

    def load(self, config_path: Path):
        """
        Lädt die YAML-Konfiguration aus der angegebenen Datei und validiert sie mit Pydantic.
        :param config_path: Pfad zur YAML-Konfigurationsdatei
        :raises ValueError: Falls kein Pfad übergeben wird oder die Datei nicht existiert.
        """
        if not isinstance(config_path, Path):
            raise ValueError("config_path muss ein pathlib.Path-Objekt sein.")
        if not config_path.exists():
            raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {config_path}")
        with open(config_path, "r") as f:
            raw_config = yaml.safe_load(f)
        try:
            # Pydantic validiert und typisiert die geladenen Daten
            self._config = ConfigData(**raw_config)
        except ValidationError as e:
            # Fehlerhafte oder unvollständige Konfiguration wird sofort erkannt
            raise ValueError(f"Fehlerhafte Konfiguration: {e}")

    @property
    def data(self) -> ConfigData:
        """
        Gibt die geladene Konfiguration als Pydantic-Modell zurück.
        :raises ValueError: Falls die Konfiguration noch nicht geladen wurde.
        """
        if self._config is None:
            raise ValueError("Config nicht geladen! Bitte zuerst load() aufrufen.")
        return self._config

    # Zugriffsmethoden geben direkt typisierte Werte aus dem Pydantic-Modell zurück
    def get_locale(self) -> str:
        return self.data.locale

    def get_currency(self) -> str:
        return self.data.currency

    def get_currency_format(self) -> str:
        return self.data.currency_format

    def get_date_format(self) -> str:
        return self.data.date_format

    def get_numeric_format(self) -> str:
        return self.data.numeric_format

    def get_expected_columns(self) -> Dict[str, Any]:
        return self.data.expected_columns

    def get_structure(self) -> StructureConfig:
        return self.data.structure

    # Optional: Allgemeiner Getter für beliebige Felder (nur für flache Felder empfohlen)
    def get(self, key: str, default=None):
        return getattr(self.data, key, default)

if __name__ == "__main__":
    # Beispiel für das Laden und Validieren der Konfiguration
    config_path = Path("wegpiraten_config.yaml")
    config = Config()
    try:
        config.load(config_path)
        print("Konfiguration erfolgreich geladen und validiert.")
        print("Projektwurzel:", config.get_structure().prj_root)
    except Exception as e:
        print(f"Fehler beim Laden der Konfiguration: {e}")
