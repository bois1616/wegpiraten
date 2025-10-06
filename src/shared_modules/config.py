import os
import sys
from pathlib import Path
from typing import Any, Optional, Dict, Type
from pydantic import BaseModel, create_model  # create_model ergänzt

import yaml
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from loguru import logger

from shared_modules.utils import get_type_from_str
from shared_modules.config_data import ConfigData
from shared_modules.provider_config import ProviderConfig
from shared_modules.structure_config import StructureConfig

# Typalias für Entity-Modelle
EntityModelDict = Dict[str, Type[BaseModel]]


class Config:
    """
    Singleton-Klasse für das Laden und Bereitstellen der Konfiguration.
    Nutzt Pydantic zur Validierung und Typisierung.
    """

    _instance: Optional["Config"] = None
    _config: Optional[ConfigData] = None
    _log_configured: bool = False
    _entity_models: Optional[EntityModelDict] = None

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
        # Nur Initialisierung, keine Typangabe mehr nötig
        self._log_configured = False
        self._entity_models = None

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
        log_file = logs_dir / (
            getattr(self, "get_log_file", lambda: "wegpiraten.log")()
        )
        # Hole Level aus der Config, fallback auf INFO
        log_level = getattr(self, "get_log_level", lambda: "INFO")()
        # Entferne alle bestehenden Handler
        logger.remove()
        # Schreibe ins Logfile
        logger.add(
            str(log_file),
            rotation="10 MB",
            retention="10 days",
            encoding="utf-8",
            level=log_level,
        )
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
            raise FileNotFoundError(
                f"Konfigurationsdatei nicht gefunden: {config_path}"
            )
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
        except Exception as e:
            # Fehlerhafte oder unvollständige Konfiguration wird sofort erkannt
            raise ValueError(f"Fehlerhafte Konfiguration: {e}")

    def get_log_file(self) -> str:
        """Gibt den Namen der Logdatei zurück (aus logging.log_file oder Default)."""
        if hasattr(self.data, "logging") and self.data.logging and self.data.logging.log_file:
            return self.data.logging.log_file
        return "wegpiraten.log"

    def get_log_level(self) -> str:
        """Gibt das Log-Level zurück (aus logging.log_level oder Default)."""
        if hasattr(self.data, "logging") and self.data.logging and self.data.logging.log_level:
            return self.data.logging.log_level
        return "INFO"

    def get_decrypted_secret(
        self, key: str, fernet_key_env: str = "FERNET_KEY", default: Any = None
    ) -> Optional[str]:
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

    def get_secret(self, key: str, default: Any = None) -> Optional[str]:
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

    def get_structure(self) -> StructureConfig:
        """Gibt die Struktur-Konfiguration zurück."""
        return self.data.structure

    def get_provider(self) -> Optional[ProviderConfig]:
        """Gibt die Provider-Konfiguration zurück (falls vorhanden)."""
        return self.data.provider

    def get(self, key: str, default: Any = None) -> Any:
        """
        Allgemeiner Getter für beliebige Felder (nur für flache Felder empfohlen).
        Args:
            key (str): Name des Feldes
            default: Optionaler Defaultwert
        Returns:
            Any: Wert des Feldes oder Default
        """
        return getattr(self.data, key, default)

    def get_entity_models(self) -> EntityModelDict:
        """
        Erzeugt und cached dynamisch Pydantic-Modelle für alle Entities aus der Config.

        Rückgabe:
            dict: Mapping von Entity-Namen auf dynamisch erzeugte Pydantic-Modelle.

        Beispiel:
            >>> config = Config()
            >>> config.load(Path("wegpiraten_config.yaml"))
            >>> entity_models = config.get_entity_models()
            >>> ClientModel = entity_models["client"]
            >>> client = ClientModel(client_id="123", first_name="Max", last_name="Muster")
            >>> print(client.dict())
            {'client_id': '123', 'first_name': 'Max', 'last_name': 'Muster', ...}
        """
        # Prüfe, ob die Modelle bereits erzeugt und gecached wurden
        if hasattr(self, "_entity_models") and self._entity_models is not None:
            return self._entity_models

        # Hole die Modell-Definitionen aus der geladenen Config
        models_config = self.get("models")
        entity_models: EntityModelDict = {}

        for entity_name, entity_def in models_config.items():
            fields = entity_def.fields
            annotations = {}
            # ...baue ein Dictionary mit Feldnamen und Typen für das Pydantic-Modell
            for field in fields:
                field_name = field.name
                if not field_name.isidentifier():
                    raise ValueError(f"Ungültiger Feldname für Pydantic in Config: {field_name}")
                typ = get_type_from_str(field.type)
                # Prüfe, ob das Feld optional ist
                if getattr(field, "optional", False):
                    typ = Optional[typ]
                    default = None
                else:
                    default = getattr(field, "default", ...)
                annotations[field_name] = (typ, default)

            logger.debug(f"Erzeuge Modell {entity_name}: {annotations}")
            entity_models[entity_name] = create_model(
                entity_name.capitalize(), **annotations
            )
        # Cache die erzeugten Modelle für spätere Aufrufe
        self._entity_models = entity_models
        return entity_models


if __name__ == "__main__":
    # Für Standalone-Tests: sys.path anpassen, damit absolute Imports funktionieren
    sys.path.append(str(Path(__file__).parent.parent))

    # Beispiel für das Laden und Validieren der Konfiguration
    config_path = Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"
    config = Config()
    try:
        config.load(config_path)
        logger.info("Projektwurzel: {}", config.get_structure().prj_root)
        # Beispiel: Zugriff auf dynamisch erzeugte Entity-Modelle
        entity_models = config.get_entity_models()
        ClientModel = entity_models["client"]
        # Beispiel-Instanz erzeugen
        client = ClientModel(client_id="123", social_security_number="756.1234.5678.97")
        logger.info("Client-Daten: {}", client.dict())
    except Exception as e:
        logger.error(f"Fehler beim Laden der Konfiguration: {e}")
