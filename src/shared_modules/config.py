import keyword
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Type

import yaml
from cryptography.fernet import Fernet
from loguru import logger
from pydantic import BaseModel

from pydantic_models.config.database_config import DatabaseConfig
from pydantic_models.config.entity_model_config import EntityModelConfig
from pydantic_models.config.formatting_config import FormattingConfig
from pydantic_models.config.logging_config import LoggingConfig
from pydantic_models.config.service_provider_config import ServiceProviderConfig

# Importiere die statischen Pydantic-Modelle direkt, wenn src im PYTHONPATH liegt
from pydantic_models.config.structure_config import StructureConfig
from pydantic_models.config.templates_config import TemplatesConfig

ModelDict = Dict[str, EntityModelConfig]

class Config:
    """
    Singleton für das Laden und Prüfen der Konfiguration.
    Nutzt statische Pydantic-Modelle für alle Abschnitte und Entities.
    Prüft Konsistenz zwischen Modellen und Config-Datei.
    Prüft, ob Feldnamen gültige Python-Bezeichner sind und keine Schlüsselwörter.
    """

    _instance: Optional["Config"] = None

    def __new__(cls, config_path: Path):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Path):
        # Fallback-Logger für Fehler beim Laden der Config
        logger.remove()
        logger.add(sys.stderr, level="WARNING")
        self.config_path = config_path
        try:
            self.raw_config: Dict[str, Any] = self._load_config()
            self.logging = self._parse_section(self.raw_config, "logging", LoggingConfig)
            self._setup_logging()
            logger.debug(f"Lade Konfiguration von {config_path}")
        except Exception as e:
            logger.error(f"Fehler beim Laden der Konfiguration: {e}")
            raise

        self.structure = self._parse_section(self.raw_config, "structure", StructureConfig)
        self.database = self._parse_section(self.raw_config, "database", DatabaseConfig)
        self.formatting = self._parse_section(self.raw_config, "formatting", FormattingConfig)
        self.service_provider = self._parse_section(self.raw_config, "service_provider", ServiceProviderConfig)
        self.templates = self._parse_section(self.raw_config, "templates", TemplatesConfig)
        self.models = self._parse_entities(self.raw_config.get("entities", {}))

        self._validate_structure_and_paths()
        self._validate_consistency()
        logger.debug("Konfiguration erfolgreich geladen und validiert.")
        self._initialized = True

    def _setup_logging(self) -> None:
        """
        Initialisiert loguru mit den Einstellungen aus der Config-Datei.
        """
        logger.remove()
        log_file = getattr(self.logging, "log_file", None)
        log_level = getattr(self.logging, "log_level", "DEBUG")
        if log_file:
            logger.add(log_file, level=log_level)
        logger.add(sys.stderr, level=log_level)

    def _load_config(self) -> Dict[str, Any]:
        """
        Lädt die YAML-Konfigurationsdatei.
        """
        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def _parse_section(self, config: Dict[str, Any], section: str, model: Type[BaseModel]) -> Any:
        """
        Parst einen Abschnitt der Config mit dem passenden Pydantic-Modell.
        """
        data = config.get(section, {})
        logger.debug(f"Parsiere Abschnitt '{section}': {data}")
        return model(**data)

    def _parse_entities(self, entities_dict: Dict[str, Any]) -> ModelDict:
        """
        Parst alle Entity-Modelle aus der Config mit dem statischen EntityModelConfig.
        """
        result = {}
        for name, entity_data in entities_dict.items():
            logger.debug(f"Parsiere Entity-Modell '{name}': {entity_data}")
            result[name] = EntityModelConfig(**entity_data)
        return result

    def _validate_consistency(self) -> None:
        """
        Prüft, ob die Entity-Modelle und Felddefinitionen mit der Config konsistent sind.
        Prüft, ob alle Feldnamen gültige Python-Bezeichner sind und keine Schlüsselwörter.
        """
        for model_name, model_config in self.models.items():
            for field in model_config.fields:
                # Prüfe Python-Bezeichner
                if not field.name.isidentifier():
                    logger.error(
                        f"Ungültiger Feldname '{field.name}' im Modell '{model_name}' (kein gültiger Python-Bezeichner)."
                    )
                    raise ValueError(
                        f"Ungültiger Feldname '{field.name}' im Modell '{model_name}' (kein gültiger Python-Bezeichner)."
                    )
                if keyword.iskeyword(field.name):
                    logger.error(
                        f"Feldname '{field.name}' im Modell '{model_name}' ist ein reserviertes Python-Schlüsselwort."
                    )
                    raise ValueError(
                        f"Feldname '{field.name}' im Modell '{model_name}' ist ein reserviertes Python-Schlüsselwort."
                    )
                # Typprüfung (optional, kann erweitert werden)
                if field.type not in {"str", "float", "int", "bool", "currency"}:
                    logger.error(
                        f"Unbekannter Typ '{field.type}' für Feld '{field.name}' im Modell '{model_name}'."
                    )
                    raise ValueError(
                        f"Unbekannter Typ '{field.type}' für Feld '{field.name}' im Modell '{model_name}'."
                    )

    def _validate_structure_and_paths(self) -> None:
        """
        Prüft einmalig alle Pfad- und Pflichtangaben. Scheitern die Prüfungen,
        wird die Konfiguration verworfen.
        """
        prj_root_raw = getattr(self.structure, "prj_root", None)
        if not prj_root_raw:
            logger.error("structure.prj_root ist nicht gesetzt.")
            raise ValueError("structure.prj_root ist Pflicht.")

        prj_root = Path(prj_root_raw).expanduser().resolve()
        if not prj_root.exists():
            logger.error(f"Projektwurzel existiert nicht: {prj_root}")
            raise FileNotFoundError(f"Projektwurzel nicht gefunden: {prj_root}")

        local_data_rel = getattr(self.structure, "local_data_path", None) or "data"
        data_dir = (prj_root / local_data_rel).resolve()
        if not data_dir.exists():
            logger.error(f"Datenverzeichnis existiert nicht: {data_dir}")
            raise FileNotFoundError(f"Datenverzeichnis nicht gefunden: {data_dir}")

        sqlite_name = getattr(self.database, "sqlite_db_name", None)
        if not sqlite_name:
            logger.error("database.sqlite_db_name ist nicht gesetzt.")
            raise ValueError("database.sqlite_db_name ist Pflicht.")

        db_path = data_dir / sqlite_name
        if not db_path.exists():
            logger.error(f"SQLite-Datenbank nicht gefunden: {db_path}")
            raise FileNotFoundError(f"SQLite-Datenbank nicht gefunden: {db_path}")

        template_rel = getattr(self.structure, "template_path", None) or "templates"
        template_dir = (prj_root / template_rel).resolve()
        if not template_dir.exists():
            logger.error(f"Template-Verzeichnis existiert nicht: {template_dir}")
            raise FileNotFoundError(f"Template-Verzeichnis nicht gefunden: {template_dir}")

        reporting_template = getattr(self.templates, "reporting_template", None)
        if not reporting_template:
            logger.error("templates.reporting_template ist nicht gesetzt.")
            raise ValueError("templates.reporting_template ist Pflicht.")

        template_file = template_dir / reporting_template
        if not template_file.exists():
            logger.error(f"Reporting-Template nicht gefunden: {template_file}")
            raise FileNotFoundError(f"Reporting-Template nicht gefunden: {template_file}")

        # optionale Import-Pfade prüfen, Warnung statt Fehler
        imports_rel = getattr(self.structure, "imports_path", None)
        if imports_rel:
            imports_path = (prj_root / imports_rel).resolve()
            if not imports_path.exists():
                logger.warning(f"Imports-Pfad existiert nicht: {imports_path}")

        # Pflichtfelder für Timesheet-Layout prüfen
        header_cfg = getattr(self.templates, "time_sheet_header_cells", None)
        row_cfg = getattr(self.templates, "time_sheet_row_mapping", None)
        start_cell = getattr(self.templates, "time_sheet_data_start_cell", None)
        end_cell = getattr(self.templates, "time_sheet_data_end_cell", None)
        missing = [
            ("templates.time_sheet_header_cells", header_cfg),
            ("templates.time_sheet_row_mapping", row_cfg),
            ("templates.time_sheet_data_start_cell", start_cell),
            ("templates.time_sheet_data_end_cell", end_cell),
        ]
        for field_name, value in missing:
            if value is None:
                logger.error(f"{field_name} ist nicht definiert.")
                raise ValueError(f"{field_name} ist Pflicht.")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Allgemeiner Getter für beliebige Felder (dot-notation für verschachtelte Felder).
        """
        parts = key.split(".")
        val = self.raw_config
        for part in parts:
            if isinstance(val, dict) and part in val:
                val = val[part]
            else:
                logger.debug(f"Feld '{key}' nicht gefunden, Rückgabe Default: {default}")
                return default
        return val

    def get_secret(self, key: str, default: Any = None) -> Optional[str]:
        """
        Gibt ein Secret (z. B. Passwort, API-Key) aus Umgebungsvariablen zurück.
        """
        logger.debug(f"Lese Secret '{key}' aus Umgebungsvariablen.")
        return os.getenv(key, default)

    def get_decrypted_secret(
        self, key: str, fernet_key_env: str = "FERNET_KEY", default: Any = None
    ) -> Optional[str]:
        """
        Holt ein verschlüsseltes Secret aus der Umgebung und entschlüsselt es mit Fernet.
        """
        encrypted = os.getenv(key)
        fernet_key = os.getenv(fernet_key_env)
        logger.debug(f"Versuche Secret '{key}' mit Fernet-Key '{fernet_key_env}' zu entschlüsseln.")
        if not encrypted or not fernet_key:
            logger.debug("Kein Secret oder Key gefunden, Rückgabe Default.")
            return default
        try:
            f = Fernet(fernet_key.encode())
            decrypted = f.decrypt(encrypted.encode())
            logger.debug("Secret erfolgreich entschlüsselt.")
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Entschlüsselung fehlgeschlagen: {e}")
            raise RuntimeError(f"Entschlüsselung fehlgeschlagen: {e}")

if __name__ == "__main__":
    config_path = (
        Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"
    )
    config = Config(config_path)
    logger.info("Projektwurzel: {}", config.structure.prj_root)
    # Validierung erfolgt beim Laden automatisch

# Fehlende Modelle:
# - Falls weitere Abschnitte in der Config existieren (z.B. templates, users, roles, ...), müssen dafür noch statische Pydantic-Modelle in pydantic_models/config.py definiert werden.
# - Für spezielle Felder (z.B. eigene Typen wie currency, date, etc.) kann ein eigener Typ in pydantic_models/config.py ergänzt werden.
