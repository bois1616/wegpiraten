import yaml
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError
from typing import Any, Optional, List

# Einzelne Spaltenbeschreibung für expected_columns
class ColumnConfig(BaseModel):
    name: str
    type: str
    format: Optional[str] = None
    is_position: Optional[bool] = None
    sum: Optional[bool] = None
    decimals: Optional[int] = None

# expected_columns ist ein Dict[str, List[ColumnConfig]]
class ExpectedColumnsConfig(BaseModel):
    payer: List[ColumnConfig] = Field(default_factory=list)
    client: List[ColumnConfig] = Field(default_factory=list)
    general: List[ColumnConfig] = Field(default_factory=list)

# Struktur-Teil der Konfiguration
class StructureConfig(BaseModel):
    prj_root: str
    data_path: Optional[str] = None
    output_path: Optional[str] = "output"
    template_path: Optional[str] = "templates"
    tmp_path: Optional[str] = ".tmp"
    logs: Optional[str] = ".logs"

# Optional: Provider-Informationen als eigenes Modell
class ProviderConfig(BaseModel):
    IBAN: Optional[str] = None
    name: Optional[str] = None
    strasse: Optional[str] = None
    plz_ort: Optional[str] = None

# Pydantic-Modell für die gesamte Konfiguration
class ConfigData(BaseModel):
    locale: str = "de_CH"                       # Gebietsschema
    currency: str = "CHF"                       # Währung
    currency_format: str = "¤#,##0.00"          # Format für Währungsangaben
    date_format: str = "dd.MM.yyyy"             # Datumsformat
    numeric_format: str = "#,##0.00"            # Zahlenformat
    expected_columns: ExpectedColumnsConfig     # Erwartete Spalten als typisiertes Modell
    structure: StructureConfig                  # Struktur-Teil (siehe oben)
    db_name: Optional[str] = None
    invoice_template_name: Optional[str] = None
    sheet_name: Optional[str] = None
    client_sheet_name: Optional[str] = None
    reporting_template: Optional[str] = None
    provider: Optional[ProviderConfig] = None

class Config:
    """
    Singleton-Klasse für das Laden und Bereitstellen der Konfiguration.
    Nutzt Pydantic zur Validierung und Typisierung.
    """

    _instance: Optional["Config"] = None  # Statische Variable für die Singleton-Instanz

    def __new__(cls) -> "Config":
        # Singleton-Pattern: Nur eine Instanz pro Prozess
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config: Optional[ConfigData] = None
        return cls._instance

    def load(self, config_path: Path) -> None:
        """
        Lädt die YAML-Konfiguration aus der angegebenen Datei und validiert sie mit Pydantic.
        Args:
            config_path (Path): Pfad zur YAML-Konfigurationsdatei
        Raises:
            ValueError: Falls kein Pfad übergeben wird oder die Datei nicht existiert.
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
        Raises:
            ValueError: Falls die Konfiguration noch nicht geladen wurde.
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

    def get_expected_columns(self) -> ExpectedColumnsConfig:
        return self.data.expected_columns

    def get_structure(self) -> StructureConfig:
        return self.data.structure

    def get_provider(self) -> Optional[ProviderConfig]:
        return self.data.provider

    # Optional: Allgemeiner Getter für beliebige Felder (nur für flache Felder empfohlen)
    def get(self, key: str, default=None) -> Any:
        return getattr(self.data, key, default)

if __name__ == "__main__":
    # Beispiel für das Laden und Validieren der Konfiguration
    config_path = Path("wegpiraten_config.yaml")
    config = Config()
    try:
        config.load(config_path)
        print("Konfiguration erfolgreich geladen und validiert.")
        print("Projektwurzel:", config.get_structure().prj_root)
        print("Erwartete Spalten (general):", [col.name for col in config.get_expected_columns().general])
    except Exception as e:
        print(f"Fehler beim Laden der Konfiguration: {e}")
