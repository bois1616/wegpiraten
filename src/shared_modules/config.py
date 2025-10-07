import os
import sys
from pathlib import Path
from typing import Any, Optional, Dict, Type, Callable
from pydantic import BaseModel, create_model
import yaml
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from loguru import logger

from shared_modules.utils import get_type_from_str

# Typalias für Entity-Modelle: Entity-Name → Pydantic-Modellklasse
EntityModelDict = Dict[str, Type[BaseModel]]

# Typalias für Config-Abschnitte: Abschnittsname → Dict mit Feldern
ConfigSectionDict = Dict[str, Dict[str, Any]]


class Config:
    """
    Singleton-Klasse für das Laden und Bereitstellen der Konfiguration.
    Nutzt Pydantic zur Validierung und Typisierung.
    Erzeugt alle relevanten Modelle dynamisch aus der zentralen Config-Datei.
    """

    _instance: Optional["Config"] = None
    _config: Optional[Dict[str, Any]] = None
    _log_configured: bool = False
    _entity_models: Optional[EntityModelDict] = None
    _section_models: Optional[Dict[str, Type[BaseModel]]] = None

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
        self._log_configured = False
        self._entity_models = None
        self._section_models = None

    def _setup_logger(self) -> None:
        """
        Initialisiert loguru mit dem Log-Dateipfad und Level aus der geladenen Config.
        Erstellt das Log-Verzeichnis falls nötig.
        """
        if self._log_configured:
            return
        structure = self.get_section("structure")
        prj_root = Path(structure.get("prj_root", "."))
        logs_dir = prj_root / structure.get("log_path", ".logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / self.get("logging.log_file", "wegpiraten.log")
        log_level = self.get("logging.log_level", "INFO")
        logger.remove()
        logger.add(
            str(log_file),
            rotation="10 MB",
            retention="10 days",
            encoding="utf-8",
            level=log_level,
        )
        logger.add(sys.stderr, level=log_level)
        self._log_configured = True

    def load(self, config_path: Path) -> None:
        """
        Lädt die YAML-Konfiguration aus der angegebenen Datei.
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
        self._config = raw_config
        # .env aus prj_root laden
        prj_root = Path(self.get("structure.prj_root", "."))
        env_path = prj_root / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
            logger.debug(f".env geladen von: {env_path}")
        else:
            logger.debug(f"Keine .env-Datei gefunden in: {env_path}")
        self._setup_logger()
        logger.info("Konfiguration erfolgreich geladen.")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Allgemeiner Getter für beliebige Felder (dot-notation für verschachtelte Felder).
        Args:
            key (str): Name des Feldes, z.B. 'structure.prj_root'
            default: Optionaler Defaultwert
        Returns:
            Any: Wert des Feldes oder Default
        """
        if self._config is None:
            raise ValueError("Config nicht geladen! Bitte zuerst load() aufrufen.")
        parts = key.split(".")
        val = self._config
        for part in parts:
            if isinstance(val, dict) and part in val:
                val = val[part]
            else:
                return default
        return val

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Gibt einen Abschnitt der Config als Dictionary zurück.
        Args:
            section (str): Abschnittsname (z.B. 'structure', 'database')
        Returns:
            Dict[str, Any]: Abschnittsdaten
        """
        if self._config is None:
            raise ValueError("Config nicht geladen! Bitte zuerst load() aufrufen.")
        return self._config.get(section, {})

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

    def get_section_model(self, section: str) -> Type[BaseModel]:
        """
        Erzeugt und cached ein Pydantic-Modell für einen Config-Abschnitt.
        Args:
            section (str): Abschnittsname (z.B. 'structure', 'database')
        Returns:
            Type[BaseModel]: Dynamisch erzeugtes Pydantic-Modell für den Abschnitt
        """
        if self._section_models is None:
            self._section_models = {}
        if section in self._section_models:
            return self._section_models[section]
        section_dict = self.get_section(section)
        # Baue das Modell aus den Feldern des Abschnitts
        fields = {k: (type(v), v) for k, v in section_dict.items()}
        model = create_model(f"{section.capitalize()}Config", **fields)
        self._section_models[section] = model
        return model

    def get_entity_models(self) -> EntityModelDict:
        """
        Erzeugt und cached dynamisch Pydantic-Modelle für alle Entities/Models aus der Config.

        Rückgabe:
            dict: Mapping von Entity-Namen auf dynamisch erzeugte Pydantic-Modelle.

        Beispiel:
            >>> config = Config()
            >>> config.load(Path("wegpiraten_config.yaml"))
            >>> entity_models = config.get_entity_models()
            >>> ClientModel = entity_models["client"]
            >>> client = ClientModel(client_id="123", first_name="Max", last_name="Muster")
            >>> print(client.model_dump())
            {'client_id': '123', 'first_name': 'Max', 'last_name': 'Muster', ...}
        """
        if self._entity_models is not None:
            return self._entity_models

        # Hole die Modell-Definitionen aus der geladenen Config
        models_config = self.get("models")
        entity_models: EntityModelDict = {}

        for entity_name, entity_def in models_config.items():
            fields = entity_def["fields"]
            annotations = {}
            # ...baue ein Dictionary mit Feldnamen und Typen für das Pydantic-Modell
            for field in fields:
                field_name = field["name"]
                if not field_name.isidentifier():
                    raise ValueError(f"Ungültiger Feldname für Pydantic in Config: {field_name}")
                typ = get_type_from_str(field["type"])
                # Optionalität und Defaultwert
                if field.get("optional", False):
                    typ = Optional[typ]
                    default = None
                else:
                    default = field.get("default", ...)
                annotations[field_name] = (typ, default)

            logger.debug(f"Erzeuge Modell {entity_name}: {annotations}")
            entity_models[entity_name] = create_model(
                entity_name.capitalize(), **annotations
            )
        # Cache die erzeugten Modelle für spätere Aufrufe
        self._entity_models = entity_models
        return entity_models

    # Beispiel für "prüfe einmal, dann vertraue": Validierung beim Laden, danach nur noch Zugriff
    def validate_config(self) -> None:
        """
        Validiert die geladene Konfiguration einmalig.
        Danach wird angenommen, dass die Daten gültig sind ("prüfe einmal, dann vertraue").
        """
        # Hier könntest du z.B. alle Entity-Modelle einmal instanziieren/testen
        entity_models = self.get_entity_models()
        for entity, model in entity_models.items():
            logger.debug(f"Validiere Entity-Modell: {entity}")
            # Test-Instanz mit Dummy-Daten (nur für Validierung, kann entfernt werden)
            try:
                dummy_data = {k: None for k in model.model_fields.keys()}
                model(**dummy_data)
            except Exception as e:
                logger.error(f"Fehler im Modell {entity}: {e}")
                raise ValueError(f"Fehler im Modell {entity}: {e}")


if __name__ == "__main__":
    # Für Standalone-Tests: sys.path anpassen, damit absolute Imports funktionieren
    sys.path.append(str(Path(__file__).parent.parent))

    # Beispiel für das Laden und Validieren der Konfiguration
    config_path = Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"
    config = Config()
    try:
        config.load(config_path)
        logger.info("Projektwurzel: {}", config.get("structure.prj_root"))
        # Zugriff auf dynamisch erzeugte Entity-Modelle
        entity_models = config.get_entity_models()
        ClientModel = entity_models["client"]
        client = ClientModel(client_id="123", first_name="Max", last_name="Muster")
        logger.info("Client-Daten: {}", client.model_dump())
        # Validierungstest
        config.validate_config()
    except Exception as e:
        logger.error(f"Fehler beim Laden der Konfiguration: {e}")
