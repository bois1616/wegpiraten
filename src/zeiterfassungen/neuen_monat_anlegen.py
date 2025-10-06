from pathlib import Path
from shared_modules.config import Config, StructureConfig

from modules.reporting_factory import ReportingFactory, ReportingFactoryConfig
from modules.reporting_processor import ReportingConfig, ReportingProcessor


def main() -> None:
    """
    Einstiegspunkt für das Anlegen eines neuen Berichtsmonats.
    Lädt die Konfiguration (validiert mit Pydantic), initialisiert Factory und Processor
    und startet die Verarbeitung. Nutzt ausschließlich Pydantic-Modelle für Konfiguration.
    Die Datenquelle ist jetzt die SQLite-Datenbank aus der Konfiguration.
    """
    # Pfad zur YAML-Konfigurationsdatei bestimmen
    config_path: Path = Path(__file__).parent.parent.parent / ".config" / "wegpiraten_config.yaml"
    config: Config = Config()
    config.load(config_path)  # Lädt und validiert die Konfiguration, initialisiert Logger

    # Zugriff auf die Struktur-Konfiguration über das Pydantic-Modell
    structure: StructureConfig = config.get_structure()

    # Die Pfade werden direkt aus dem Pydantic-Modell gelesen
    prj_root: Path = Path(structure.prj_root)
    output_path: Path = prj_root / (structure.output_path or "output")
    template_path: Path = prj_root / (structure.template_path or "templates")

    # Zugriff auf die SQLite-Datenbank aus der Konfiguration
    local_data_path: Path = Path(structure.local_data_path or "data")
    sqlite_db_name: str = config.data.database.sqlite_db_name
    db_path: Path = prj_root / local_data_path / sqlite_db_name

    # TODO: Erweiterung: ReportingFactory- und ReportingProcessor-Konfiguration auslagern
    # Diese Blöcke prüfen, ob die Konfiguration in der Hauptkonfiguration vorhanden ist,
    # und nutzen ansonsten Defaultwerte der jeweiligen Pydantic-Modelle.

    # ReportingFactoryConfig aus der Hauptkonfiguration extrahieren (falls vorhanden)
    factory_config_data: dict = getattr(config.data, "reporting_factory", {})
    factory_config: ReportingFactoryConfig = ReportingFactoryConfig(**factory_config_data)
    factory: ReportingFactory = ReportingFactory(factory_config)

    # ReportingConfig aus der Hauptkonfiguration extrahieren (falls vorhanden)
    reporting_config_data: dict = getattr(config.data, "reporting_processor", {})
    reporting_config_data["structure"] = structure
    reporting_config_data["db_path"] = db_path  # <-- SQLite-DB statt Excel!
    
    reporting_config: ReportingConfig = ReportingConfig(**reporting_config_data)
    processor: ReportingProcessor = ReportingProcessor(reporting_config, factory)

 # Monat für die Erfassungsbögen festlegen (z.B. als YYYY-MM)
    reporting_month: str = "2025-10"

    # Ausführung der Verarbeitung mit typisierten Pfaden und Monat
    processor.run(reporting_month, output_path, template_path)


if __name__ == "__main__":
    main()