import os
import sys
from pathlib import Path
from typing import Any, Optional

import yaml  # YAML-Parser für das Einlesen der Konfigurationsdatei
from cryptography.fernet import Fernet  # Für die Entschlüsselung von Secrets
from dotenv import load_dotenv  # Lädt Umgebungsvariablen aus einer .env-Datei
from pydantic import ValidationError  # Für die Validierung der Konfigurationsdaten
from loguru import logger  # Leistungsfähiges Logging-Framework

# Eigene Pydantic-Modelle für die Konfigurationsstruktur importieren
from .expected_columns_config import ExpectedColumnsConfig
from .provider_config import ProviderConfig
from .structure_config import StructureConfig
from .config_data import ConfigData  # Zentrale Konfigurationsdatenstruktur

class Config:
    """
    Singleton-Klasse für das Laden und Bereitstellen der Konfiguration.
    Nutzt Pydantic zur Validierung und Typisierung.
    """

    _instance: Optional["Config"] = None

    def __new__(cls) -> "Config":
        """
        Stellt sicher, dass nur eine Instanz der Config-Klasse existiert (Singleton).
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initialisiert die Konfigurationsinstanz.
        """
        if not hasattr(self, "_config"):
            self._config: Optional[ConfigData] = None
        self._log_configured = False

    def _setup_logger(self):
        """
        Initialisiert loguru mit dem Log-Dateipfad und Level aus der geladenen Config.
        Erstellt das Log-Verzeichnis falls nötig.
        """
        if self._log_configured:
            return
        # Hole Log-Pfade und Level aus der Config
        structure = self.get_structure()
        prj_root = Path(structure.prj_root)
        logs_dir = prj_root / (getattr(structure, "log_path", ".logs") or ".logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / (getattr(self, "get_log_file", lambda: "wegpiraten.log")())
        # Hole Level aus der Config, fallback auf INFO
        log_level = getattr(self, "get_log_level", lambda: "INFO")()
        # Entferne alle bestehenden Handler
        logger.remove()
        # Schreibe ins Logfile
        logger.add(str(log_file), rotation="10 MB", retention="10 days", encoding="utf-8", level=log_level)
        # Schreibe auch ins Terminal ab log_level
        logger.add(sys.stderr, level=log_level)
        self._log_configured = True

    def load(self, config_path: Path) -> None:
        """
        Lädt die YAML-Konfiguration aus der angegebenen Datei und validiert sie mit Pydantic.
        Lädt zusätzlich die .env-Datei aus dem Projekt-Root.
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
            self._config = ConfigData(**raw_config)
            # .env aus prj_root laden
            prj_root = Path(self._config.structure.prj_root)
            env_path = prj_root / ".env"
            if env_path.exists():
                load_dotenv(dotenv_path=env_path, override=True)
                logger.debug(f".env geladen von: {env_path}")
            else:
                logger.debug(f"Keine .env-Datei gefunden in: {env_path}")
            self._setup_logger()
            logger.info("Konfiguration erfolgreich geladen und validiert.")
        except ValidationError as e:
            # Fehlerhafte oder unvollständige Konfiguration wird sofort erkannt
            raise ValueError(f"Fehlerhafte Konfiguration: {e}")

    def get_log_file(self) -> str:
        # log_file kann in der Config auf Top-Level oder in structure stehen
        if hasattr(self.data, "log_file") and self.data.log_file:
            return self.data.log_file
        if hasattr(self.data.structure, "log_file") and self.data.structure.log_file:
            return self.data.structure.log_file
        return "wegpiraten.log"

    def get_log_level(self) -> str:
        # log_level kann auf Top-Level stehen, fallback auf INFO
        return getattr(self.data, "log_level", "INFO")

    def get_decrypted_secret(self, key: str, fernet_key_env: str = "FERNET_KEY", default=None) -> Optional[str]:
        """
        Holt ein verschlüsseltes Secret aus der Umgebung und entschlüsselt es mit Fernet.
        Args:
            key (str): Name der Umgebungsvariable mit dem verschlüsselten Secret
            fernet_key_env (str): Name der Umgebungsvariable mit dem Fernet-Key
            default: Optionaler Defaultwert
        Returns:
            Optional[str]: Entschlüsseltes Secret oder Default
        Raises:
            RuntimeError: Falls die Entschlüsselung fehlschlägt.
        """
        encrypted = os.getenv(key)
        fernet_key = os.getenv(fernet_key_env)
        logger.debug(f"{key} aus env: {encrypted}")
        logger.debug(f"{fernet_key_env} aus env: {fernet_key}")
        if not encrypted or not fernet_key:
            logger.debug("Secret oder Key nicht gefunden!")
            return default
        try:
            f = Fernet(fernet_key.encode())
            decrypted = f.decrypt(encrypted.encode())
            logger.debug("Secret erfolgreich entschlüsselt.")
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Entschlüsselung fehlgeschlagen: {e}")
            raise RuntimeError(f"Entschlüsselung fehlgeschlagen: {e}")

    def get_secret(self, key: str, default=None) -> Optional[str]:
        """
        Gibt ein Secret (z. B. Passwort, API-Key) aus Umgebungsvariablen zurück.
        Args:
            key (str): Name der Umgebungsvariable
            default: Optionaler Defaultwert
        Returns:
            Optional[str]: Wert der Umgebungsvariable oder Default
        """
        return os.getenv(key, default)

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
        """Gibt das Gebietsschema zurück."""
        return self.data.locale

    def get_currency(self) -> str:
        """Gibt die Währung zurück."""
        return self.data.currency

    def get_currency_format(self) -> str:
        """Gibt das Währungsformat zurück."""
        return self.data.currency_format

    def get_date_format(self) -> str:
        """Gibt das Datumsformat zurück."""
        return self.data.date_format

    def get_numeric_format(self) -> str:
        """Gibt das Zahlenformat zurück."""
        return self.data.numeric_format

    def get_expected_columns(self) -> ExpectedColumnsConfig:
        """Gibt die erwarteten Spaltenkonfigurationen zurück."""
        return self.data.expected_columns

    def get_structure(self) -> StructureConfig:
        """Gibt die Struktur-Konfiguration zurück."""
        return self.data.structure

    def get_provider(self) -> Optional[ProviderConfig]:
        """Gibt die Provider-Konfiguration zurück (falls vorhanden)."""
        return self.data.provider

    def get(self, key: str, default=None) -> Any:
        """
        Allgemeiner Getter für beliebige Felder (nur für flache Felder empfohlen).
        Args:
            key (str): Name des Feldes
            default: Optionaler Defaultwert
        Returns:
            Any: Wert des Feldes oder Default
        """
        return getattr(self.data, key, default)

if __name__ == "__main__":
    # Beispiel für das Laden und Validieren der Konfiguration
    config_path = Path("wegpiraten_config.yaml")
    config = Config()
    try:
        config.load(config_path)
        logger.info("Projektwurzel: {}", config.get_structure().prj_root)
        logger.info("Erwartete Spalten (general): {}", [col.name for col in config.get_expected_columns().general])
    except Exception as e:
        logger.error(f"Fehler beim Laden der Konfiguration: {e}")
